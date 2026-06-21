---
name: pdf-signature-flatten
description: 'Flatten signature images in PDF files to remove the clickable selection frame shown by PDF viewers like PDFgear, Adobe, browsers. Use when: a signature image shows a selection border/frame on click; a PDF has clickable/selectable image objects that should not be interactively selectable; need to merge embedded signature images into page content; flatten PDF signatures without destroying text or making the whole page a raster image. Preserves text, vectors, and file size. Handles RGB, Gray, CMYK, Indexed colorspaces, SMask transparency, multi-page PDFs, array Contents streams, and Form XObjects.'
argument-hint: 'path to signed PDF or folder of signed PDFs'
---

# PDF Signature Flatten

Removes the clickable selection frame from signature images embedded in PDFs by converting the image XObject to vector path geometry directly in the page content stream. Text, vectors and file size are preserved — no full-page rasterization.

## When to Use

- A PDF opened in PDFgear / Adobe / browser shows a rectangular selection frame around the signature on click
- Need to deliver "clean" signed documents without interactive image objects
- Flattening must preserve copy-pasteable text and keep file size small

## How It Works

The signature is stored as an image XObject (`/XObject /Subtype /Image`). PDF viewers allow selecting individual XObjects, which causes the frame. This skill replaces the XObject call with equivalent vector fill rectangles built pixel-by-pixel from the decoded image data (compositing any transparency mask). The XObject entry is then removed from `/Resources`.

## Procedure

1. **Identify input** — a single PDF or a folder of PDFs to process in batch
2. **Run the script**:
   ```
   python [vectorize_signature_images.py](./scripts/vectorize_signature_images.py) <input.pdf> <output.pdf>
   ```
3. **Batch mode** — for multiple files, loop:
   ```powershell
   Get-ChildItem "*.pdf" | ForEach-Object {
       python vectorize_signature_images.py $_.FullName ($_.BaseName + "_FLAT.pdf")
   }
   ```
4. **Verify** the output in the target viewer — signature should look identical but clicking it no longer shows a frame

## Supported Cases

| Case | Supported |
|---|---|
| `/DeviceRGB` image | ✅ |
| `/DeviceGray` image | ✅ |
| `/DeviceCMYK` image | ✅ |
| `/Indexed` colorspace | ✅ |
| `/SMask` soft transparency | ✅ |
| `/Mask` stencil mask | ✅ |
| Multi-page PDFs | ✅ |
| `/Contents` as array of streams | ✅ |
| Image inside Form XObject | ✅ |
| Password-protected PDFs | ❌ decrypt first |
| Cryptographic digital signatures | ❌ flattening breaks cert validation by design |
| 1-bit images (`/BitsPerComponent 1`) | ❌ rare, not implemented |

## Dependencies

Requires `pypdf` (pure Python, no native deps):
```
pip install pypdf
```

## Script

[vectorize_signature_images.py](./scripts/vectorize_signature_images.py)
