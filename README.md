# claude-skills

Personal Claude / Copilot agent skills and working notes.

## Structure

- **`<skill-name>/`** — one directory per agent skill, usable with Claude Code (drop into `~/.claude/skills/`).
  - [`fix-sandbox-ssh-key`](fix-sandbox-ssh-key/) — refresh a Docker sandbox's SSH host key in `known_hosts` after the container regenerates it.
  - [`pdf-signature-flatten`](pdf-signature-flatten/) — flatten signature images in PDFs so viewers no longer show a clickable selection frame.
- **[`docs/`](docs/)** — approaches and working rules worth preserving independently of any one machine or project.
  - [`ai-memory-approach.md`](docs/ai-memory-approach.md) — file-based AI memory: the disposable-session loop and 5 memory hygiene rules.
