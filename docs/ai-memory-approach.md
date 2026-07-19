# File-Based AI Memory — Approach & Hygiene Rules

*Preserved 2026-07-19. Source: Reddit r/ClaudeAI, post "I gave my forgetful AI a memory" (https://www.reddit.com/r/ClaudeAI/comments/1v0d8zw/) plus the comment discussion; analyzed and adopted as working rules.*

## Core idea

AI chats forget everything when they close. Therefore: **the chat is a disposable worker; the memory lives in plain text files.** Every session reads the files on boot, does its work, and writes back what it learned before it ends. The next session boots from the same files — nothing is lost.

## The loop (one session)

1. **Boot:** read the rule/memory files
2. **Reconcile:** check "open items" against reality before trusting them
3. **Recall instead of re-derive:** ask the memory first, compute second
4. **Work through real tools**, verify live — no "should work"
5. **Log evidence** (append-only history)
6. **Irreversible actions stay with the human**
7. **Sync back:** write what was learned into the files → session ends

Honesty principle: facts carry a status (CURRENT / STALE / UNKNOWN). Only CURRENT may be stated as fact — an honest "I don't know" beats a confident wrong answer every time.

## The 5 hygiene rules

1. **Edit, don't accumulate** — if a file on the topic exists, update it; no duplicate notes. Correct or delete outdated facts immediately. (Append-only memory eventually yields three notes on the same thing, and the model picks the stale one.)
2. **Make supersession visible** — record changes as a trajectory: "X (date) → corrected to Y (date)", never silently overwrite. Prevents a later search from hitting the old version first and citing it as current.
3. **Date perishable facts** — state-of-the-world entries (statuses, versions, open items) get an absolute date. Guards against the "CURRENT-but-wrong" problem: facts that were true when written and quietly expired.
4. **Live check beats memory** — if reality contradicts a memory entry, the live check wins, and the file is corrected in the same breath (otherwise the wrong note outlives the correction).
5. **Keep the index short** — the index file stays a terse one-line-per-entry list. Once the boot reading list gets long, the model starts skimming — and you're back to confident guessing, just with extra steps.

## Installation (Claude Code)

Copy the 5-rules block from this document into the user-level file `~/.claude/CLAUDE.md` (Windows: `%USERPROFILE%\.claude\CLAUDE.md`) — that's all. It is loaded into every session on the machine, across all projects. Claude Code provides the rest out of the box (boot-read of CLAUDE.md, file-based auto-memory with a per-project index file).

Where the pieces live on a specific machine belongs in that project's memory, not in this document.

**Maintenance:** event-driven — clean up while writing/reading (rules 1+4). Run a consolidation pass manually when needed; a schedule only pays off once the memory grows to a few dozen entries.
