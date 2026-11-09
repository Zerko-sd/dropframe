# Using dropframe with other agents

dropframe is a standard [Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview): one `SKILL.md` plus a `scripts/` folder. Any agent that can read instructions and run Python can use it.

## Agents with skill discovery

This repo exposes the skill at each agent's standard path through symlinks to `skills/dropframe/`:

| Agent | Path it reads |
|---|---|
| Claude Code | `.claude/skills/dropframe/` (or the plugin install) |
| Codex CLI | `.agents/skills/dropframe/` |
| opencode | `.opencode/skills/dropframe/` |
| Google Antigravity | `.agents/skills/dropframe/`, or `~/.gemini/config/skills/dropframe/` globally |

Or use the skills CLI for any of them:

```bash
npx skills add https://github.com/Zerko-sd/dropframe --skill dropframe      # this project
npx skills add https://github.com/Zerko-sd/dropframe --skill dropframe -g   # every project
```

## Agents with custom instructions only

1. Copy `skills/dropframe/` somewhere in your project (e.g. `tools/dropframe/`).
2. Add to your agent's custom instructions:

   > When I ask for a trailer, promo, reel or any beat-synced video, read `tools/dropframe/SKILL.md` and follow it. Its scripts are in `tools/dropframe/scripts/`.

## Windows

Symlinks need `git config core.symlinks true` (or `git clone -c core.symlinks=true ...`) plus Developer Mode or admin rights. If they don't work on your system, copy `skills/dropframe/` into your agent's skill folder instead.
