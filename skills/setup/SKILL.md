---
name: setup
description: Turn on the Gatewayz status line (tokens, this session's real Gatewayz spend, credits left). Use when the user asks to set up, enable, update or remove the Gatewayz status line or token tracker.
---

# Set up the Gatewayz status line

Claude Code plugins cannot set the status line themselves, so this skill does it with the user's OK.

1. **Copy the script to a stable path.** Plugin folders change on every update, so the status line must not point into them. Show the user this command and run it once they agree:
   ```bash
   mkdir -p ~/.gatewayz/bin && cp "${CLAUDE_PLUGIN_ROOT}/bin/gatewayz-statusline" ~/.gatewayz/bin/ && chmod +x ~/.gatewayz/bin/gatewayz-statusline
   ```
2. **Check for an existing status line.** Read `~/.claude/settings.json`. If it already has a `statusLine` entry, show it to the user and ask whether to replace it. Never overwrite it silently.
3. **Ask before editing settings.json.** Show the exact change, and make it only after the user says yes:
   ```json
   "statusLine": { "type": "command", "command": "~/.gatewayz/bin/gatewayz-statusline" }
   ```
   Change only that key and keep everything else in the file.
4. **Explain how the key is found.** The script reads the key from `ANTHROPIC_AUTH_TOKEN`, which Claude Code already uses when it runs on Gatewayz, or from `GATEWAYZ_API_KEY`. Never ask the user to paste the key into the chat, and never write it to a file.
5. **Exact per-session spend (optional).** Each session needs its own tag:
   ```bash
   export ANTHROPIC_CUSTOM_HEADERS="x-gatewayz-tag: cc-$(date +%s)-$RANDOM"
   ```
   Without a tag, spend is an estimate, marked `~`. The estimate is the balance drop since the session started, so other sessions using the same key are counted in it too.
6. **Verify.** Run the script with a sample and show the user the output line:
   ```bash
   echo '{"session_id":"test","model":{"display_name":"test"}}' | ~/.gatewayz/bin/gatewayz-statusline
   ```

To update, repeat step 1. To remove, delete the `statusLine` key (with the user's OK) and `~/.gatewayz/bin/gatewayz-statusline`.
