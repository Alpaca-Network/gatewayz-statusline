# gatewayz-statusline

Live token and spend tracker for [Claude Code](https://claude.com/claude-code) sessions running on [Gatewayz](https://gatewayz.ai):

```
Gatewayz · moonshot/kimi-k2.6 · ↑182k ↓9.4k tok · $0.43 this session · $12.30 left
```

- **Tokens:** summed from the session transcript. Sent (`↑`) includes cache reads and writes. Each response is counted once.
- **This session:** what Gatewayz actually billed.
  - **Exact** when the session sends an `x-gatewayz-tag` header. The script reads it from `GET /v1/usage?tag=…`.
  - **Approximate (`~`)** otherwise: your credits at session start minus your credits now. Other sessions using the same key are included in that number.
- **Left:** your credit balance, from `GET /user/balance`.

Claude Code's own cost display uses Anthropic list prices. Those are wrong for every non-Claude model on Gatewayz, so this script never shows that number.

It needs nothing beyond Python 3.9+ (standard library only). Network calls are cached for 30 s and time out after 3 s. If anything fails, that part of the line is dropped and the status line keeps working. Your API key is read from the environment and is never printed or written to disk.

## Install

```bash
git clone https://github.com/Alpaca-Network/gatewayz-statusline ~/.gatewayz/gatewayz-statusline
```

Add to `~/.claude/settings.json`, or pass it to a single session with `claude --settings '…'`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "~/.gatewayz/gatewayz-statusline/bin/gatewayz-statusline"
  }
}
```

The script uses the same environment as your Gatewayz session:

| Variable | Use |
|---|---|
| `ANTHROPIC_AUTH_TOKEN` (or `GATEWAYZ_API_KEY`) | Your Gatewayz key |
| `ANTHROPIC_BASE_URL` (or `GATEWAYZ_BASE_URL`) | Defaults to `https://api.gatewayz.ai` |
| `ANTHROPIC_CUSTOM_HEADERS` | Add `x-gatewayz-tag: <unique-id>` to get exact per-session spend |
| `GATEWAYZ_STATUSLINE_CACHE_SECONDS` | Default `30` |

For exact spend, give each session its own tag:

```bash
export ANTHROPIC_CUSTOM_HEADERS="x-gatewayz-tag: cc-$(date +%s)-$RANDOM"
```

State (token offsets, balance cache, session baselines) lives in `~/.gatewayz/statusline/`. The folder is created with mode 0700.

## Test

```bash
python3 -m unittest discover tests
```

The tests run against a local fake API. They make no network calls and need no key.

## Roadmap

- Package as a Claude Code plugin.
- Same tracker for OpenCode and other harnesses.
- Count sub-agent transcripts in the token total.

## License

MIT
