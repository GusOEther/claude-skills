---
name: fix-sandbox-ssh-key
description: Refresh the vvstb-sandbox Docker container's SSH host key in the Windows known_hosts so the Claude desktop app can (re)connect to vscode@127.0.0.1:2222. Use whenever connecting the vvstb-sandbox SSH environment fails with "host denied", "host key verification failed", or "remote host identification has changed" — this happens after every `docker compose up --build` because the container regenerates its host key.
---

# Fix sandbox SSH host key

The `vvstb-sandbox` container (project `vvGmbH-stb-sim`) runs sshd on `127.0.0.1:2222`.
The Claude **desktop app** connects via **Windows OpenSSH**, which checks
`%USERPROFILE%\.ssh\known_hosts`. After a `docker compose up --build` the container
regenerates its SSH host key, so the stored entry no longer matches and the app
refuses to connect ("Host denied" / "Host key verification failed"). This skill
removes the stale entry and stores the current one.

## Steps

1. Confirm the container is up (start it if not):
   ```bash
   docker ps --filter name=vvstb-sandbox
   # if missing, from the vvGmbH-stb-sim folder: docker compose up -d
   ```

2. Refresh the host key in the **Windows** known_hosts. Pick the variant for the
   shell you are in:

   **Git Bash (the default Claude Code shell on this machine):**
   ```bash
   mkdir -p "$USERPROFILE/.ssh"
   ssh-keygen -f "$USERPROFILE/.ssh/known_hosts" -R "[127.0.0.1]:2222" 2>/dev/null || true
   ssh-keyscan -p 2222 127.0.0.1 >> "$USERPROFILE/.ssh/known_hosts" 2>/dev/null
   grep 2222 "$USERPROFILE/.ssh/known_hosts"
   ```

   **WSL (manual):**
   ```bash
   WIN_SSH="/mnt/c/Users/Mark/.ssh"   # adjust the Windows username if different
   mkdir -p "$WIN_SSH"
   ssh-keygen -f "$WIN_SSH/known_hosts" -R "[127.0.0.1]:2222" 2>/dev/null || true
   ssh-keyscan -p 2222 127.0.0.1 >> "$WIN_SSH/known_hosts" 2>/dev/null
   grep 2222 "$WIN_SSH/known_hosts"
   ```

   **PowerShell (manual):**
   ```powershell
   ssh-keygen -f "$env:USERPROFILE\.ssh\known_hosts" -R "[127.0.0.1]:2222"
   ssh-keyscan -p 2222 127.0.0.1 | Out-File -Append -Encoding ascii "$env:USERPROFILE\.ssh\known_hosts"
   ```

3. Reconnect the `vvstb-sandbox` environment in the Claude desktop app (New session →
   environment `vvstb-sandbox`). The host-key error should be gone.

## If it is NOT a host-key error
- `Permission denied (publickey)` → auth problem, not host key. Check that the public
  key in `vvGmbH-stb-sim/.devcontainer/authorized_keys` matches
  `%USERPROFILE%\.ssh\id_ed25519.pub`, and that the container was restarted
  (`docker compose restart`) after the key was added so the entrypoint installed it.
- `Connection refused` → the container/sshd is not running. `docker compose up -d`.

Re-run this skill after every `docker compose up --build`.
