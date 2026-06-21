from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Optional

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject, DecodedStreamObject, IndirectObject,
    NameObject, DictionaryObject,
)


def _resolve(obj: object) -> object:
    return obj.get_object() if isinstance(obj, IndirectObject) else obj


def _rgb_and_alpha(xobj: dict) -> tuple[int, int, bytes, Optional[bytes]]:
    width = int(xobj.get('/Width'))
    height = int(xobj.get('/Height'))
    bpc = int(xobj.get('/BitsPerComponent', 8))
    if bpc != 8:
        raise ValueError('Only 8-bit images are supported')

    raw = xobj.get_data()
    cs = _resolve(xobj.get('/ColorSpace'))

    # Handle /Indexed colorspace: /Indexed base hival lookup
    if isinstance(cs, ArrayObject) and len(cs) == 4 and _resolve(cs[0]) == NameObject('/Indexed'):
        base = _resolve(cs[1])
        hival = int(cs[2])
        table_obj = _resolve(cs[3])
        table: bytes = table_obj if isinstance(table_obj, bytes) else table_obj.get_data()
        # Determine components of base colorspace
        if _resolve(base) in (NameObject('/DeviceRGB'), NameObject('/RGB')):
            comp = 3
        elif _resolve(base) in (NameObject('/DeviceGray'), NameObject('/G')):
            comp = 1
        elif _resolve(base) in (NameObject('/DeviceCMYK'), NameObject('/CMYK')):
            comp = 4
        else:
            comp = 3
        out = bytearray(width * height * 3)
        for i, idx in enumerate(raw):
            idx = min(idx, hival)
            entry = table[idx * comp:(idx + 1) * comp]
            j = i * 3
            if comp == 3:
                out[j], out[j + 1], out[j + 2] = entry[0], entry[1], entry[2]
            elif comp == 1:
                out[j] = out[j + 1] = out[j + 2] = entry[0]
            elif comp == 4:
                c, m, y, k = entry[0] / 255.0, entry[1] / 255.0, entry[2] / 255.0, entry[3] / 255.0
                out[j] = int(round(255 * (1 - c) * (1 - k)))
                out[j + 1] = int(round(255 * (1 - m) * (1 - k)))
                out[j + 2] = int(round(255 * (1 - y) * (1 - k)))
        rgb = bytes(out)
        cs = NameObject('/DeviceRGB')
    else:
        rgb = None

    if cs == NameObject('/DeviceRGB') and rgb is None:
        if len(raw) != width * height * 3:
            raise ValueError('Unexpected RGB size')
        rgb = raw
    elif cs == NameObject('/DeviceGray') and rgb is None:
        if len(raw) != width * height:
            raise ValueError('Unexpected Gray size')
        out = bytearray(width * height * 3)
        for i, g in enumerate(raw):
            j = i * 3
            out[j] = g
            out[j + 1] = g
            out[j + 2] = g
        rgb = bytes(out)
    elif cs == NameObject('/DeviceCMYK') and rgb is None:
        if len(raw) != width * height * 4:
            raise ValueError('Unexpected CMYK size')
        out = bytearray(width * height * 3)
        for i in range(width * height):
            c = raw[i * 4] / 255.0
            m = raw[i * 4 + 1] / 255.0
            y = raw[i * 4 + 2] / 255.0
            k = raw[i * 4 + 3] / 255.0
            j = i * 3
            out[j] = int(round(255 * (1 - c) * (1 - k)))
            out[j + 1] = int(round(255 * (1 - m) * (1 - k)))
            out[j + 2] = int(round(255 * (1 - y) * (1 - k)))
        rgb = bytes(out)
    elif rgb is None:
        raise ValueError(f'Unsupported colorspace: {cs}')

    # /SMask soft transparency mask
    smask = xobj.get('/SMask')
    alpha: Optional[bytes] = None
    if smask is not None:
        sobj = _resolve(smask)
        alpha = sobj.get_data()
        if len(alpha) != width * height:
            alpha = None

    # /Mask as stencil (1-bit): treat as hard transparency
    mask = xobj.get('/Mask')
    if alpha is None and mask is not None:
        mask_obj = _resolve(mask)
        if isinstance(mask_obj, DictionaryObject):
            mask_raw = mask_obj.get_data()
            if len(mask_raw) == width * height:
                alpha = bytes(255 if b else 0 for b in mask_raw)

    return width, height, rgb, alpha


def _vector_rects_for_signature(width: int, height: int, rgb: bytes, alpha: bytes | None) -> bytes:
    # Build run-length encoded black rectangles in normalized image space [0..1].
    # This renders as vector paths under the existing page transformation matrix.
    lines: list[str] = ["0 g\n"]

    rect_count = 0
    for row in range(height):
        runs: list[tuple[int, int]] = []
        run_start = -1

        for col in range(width):
            i = (row * width + col) * 3
            r, g, b = rgb[i], rgb[i + 1], rgb[i + 2]
            luma = 0.299 * r + 0.587 * g + 0.114 * b

            a = alpha[row * width + col] if alpha is not None else 255
            darkness = (255.0 - luma) * (a / 255.0)

            is_ink = darkness >= 28.0

            if is_ink and run_start < 0:
                run_start = col
            elif not is_ink and run_start >= 0:
                runs.append((run_start, col))
                run_start = -1

        if run_start >= 0:
            runs.append((run_start, width))

        if not runs:
            continue

        y = (height - 1 - row) / height
        h = 1.0 / height

        for x0, x1 in runs:
            x = x0 / width
            w = (x1 - x0) / width
            lines.append(f"{x:.6f} {y:.6f} {w:.6f} {h:.6f} re\n")
            rect_count += 1

    if rect_count == 0:
        return b''

    lines.append("f\n")
    return ''.join(lines).encode('ascii')


def _get_content_data(page) -> bytes:
    """Decode /Contents whether it is a single stream or an array of streams."""
    cobj = page.get('/Contents')
    if cobj is None:
        return b''
    cobj = _resolve(cobj)
    if isinstance(cobj, ArrayObject):
        return b'\n'.join(_resolve(s).get_data() for s in cobj)
    return cobj.get_data()


def _set_content_data(page, data: bytes) -> None:
    """Replace /Contents with a single decoded stream."""
    new_stream = DecodedStreamObject()
    new_stream.set_data(data)
    page[NameObject('/Contents')] = new_stream


def _process_xobjects(xobjects: dict, data: bytes) -> tuple[bytes, int]:
    """Replace image XObject Do calls with vector rects in-place within data."""
    replaced = 0
    for xname, xref in list(xobjects.items()):
        xobj = _resolve(xref)
        if xobj.get('/Subtype') != NameObject('/Image'):
            continue

        token = re.escape(f'{xname} Do'.encode('latin1'))
        pattern = re.compile(rb'(?<!\S)' + token + rb'(?!\S)')
        if not pattern.search(data):
            continue

        try:
            width, height, rgb, alpha = _rgb_and_alpha(xobj)
            replacement = _vector_rects_for_signature(width, height, rgb, alpha)
        except Exception:
            continue

        if not replacement:
            continue

        data, n = pattern.subn(lambda _m: replacement, data)
        if n:
            replaced += n
            try:
                del xobjects[xname]
            except Exception:
                pass

    return data, replaced


def vectorize_signature_images(input_pdf: Path, output_pdf: Path) -> tuple[int, int]:
    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()

    pages_changed = 0
    total_replaced = 0

    for page in reader.pages:
        resources = page.get('/Resources') or {}
        xobjects = resources.get('/XObject')

        changed = False
        replaced_count = 0

        if xobjects:
            data = _get_content_data(page)
            if data:
                # Replace images directly in page content
                new_data, n = _process_xobjects(xobjects, data)
                if n:
                    _set_content_data(page, new_data)
                    replaced_count += n
                    changed = True

        # Also recurse into Form XObjects on this page
        if xobjects:
            for xname, xref in list((xobjects or {}).items()):
                xobj = _resolve(xref)
                if xobj.get('/Subtype') != NameObject('/Form'):
                    continue
                inner_res = xobj.get('/Resources') or {}
                inner_xobjs = inner_res.get('/XObject')
                if not inner_xobjs:
                    continue
                try:
                    inner_data = xobj.get_data()
                except Exception:
                    continue
                new_inner, n = _process_xobjects(inner_xobjs, inner_data)
                if n:
                    xobj.set_data(new_inner)
                    replaced_count += n
                    changed = True

        if changed:
            pages_changed += 1
            total_replaced += replaced_count

        writer.add_page(page)

    with output_pdf.open('wb') as f:
        writer.write(f)

    return pages_changed, total_replaced


def main() -> None:
    parser = argparse.ArgumentParser(description='Replace signature image XObjects with vector path rectangles.')
    parser.add_argument('input_pdf', type=Path)
    parser.add_argument('output_pdf', type=Path)
    args = parser.parse_args()

    p, r = vectorize_signature_images(args.input_pdf, args.output_pdf)
    print(f'Changed pages: {p}')
    print(f'Replacements: {r}')
    print(f'Output: {args.output_pdf}')


if __name__ == '__main__':
    main()
