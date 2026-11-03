# Installation and four optional recommendations

## Setup entry

A `SKILL.md` file has no universal installation hook. `npx skills add` and copying folders install skill files; they do not run this Python setup or show the custom dependency question. The supported interactive entry below asks during installation. For a plain skills-manager install, the agent asks on first use if no choice is known.

From the downloaded/cloned repository with Python 3.9+:

```bash
python3 scripts/install.py --agent codex
python3 scripts/install.py --agent claude-code
python3 scripts/install.py --agent generic --dest /absolute/agent/skills
```

The installer lists four projects and pinned revisions, then asks `all / none / selected keys`; Enter means none. Non-interactive mode leaves recommendations pending unless explicitly passed `--recommended all`, `--recommended none` or keys such as `remotion,shotcraft`. An agent must obtain the user's choice before passing a selection flag. `--dry-run` writes/downloads nothing.

| Recommended project | Role | Extra runtime requirements |
| --- | --- | --- |
| HyperFrames | HTML/CSS/GSAP composition | Actual CLI/browser and required Node; official core includes three companion skill entries shown before installation |
| Video Use | Source editing/speech-aware timing | Separate Python environment/helpers; speech transcription can use a metered external service |
| Remotion Agent Skills | React video production guidance | Real project, packages and browser; renderer terms remain independent |
| Video Shotcraft | Shot recipes/motion/sound design | Selected engine; per-asset attribution still applies |

The exact repositories, revisions and entries are in [recommended-skills.json](../recommended-skills.json). This package does not vendor these projects. The installer fetches selected skill files only after consent. A pinned commit provides reproducible source selection, not a guarantee of compatibility. Existing skill directories are preserved and reported as `preserved_existing`, never silently upgraded.

Skill installation does **not** install FFmpeg, Node, Python environments, render engines, desktop apps, accounts or credentials. It does not execute upstream install.md, npm/uv/package hooks, or paid-service setup. Reload/rescan the host, run route-specific preflight and a real small sample before a full film.

## First use

If unresolved ask once: “Install all four recommended skill projects, selected ones, or skip?” Reuse an existing answer. Declining keeps base writing/subtitle/local validation available. Check the selected engine before rendering; do not pretend missing effects were reproduced.

Explain optional Jianying narration and offer existing audio / manual export / none. Do not ask again if already declined; do not launch desktop apps or request speech-service keys for no-narration work.

## Discovery

`scripts/skill_paths.py` checks sibling skills; project `.agents/skills`, `.claude/skills`, `.codex/skills`, `.cursor/skills`; user skill roots; and existing Codex HyperFrames plugin caches. Custom roots use `CUT_STATION_SKILL_PATHS` (OS path separator) or per-project `--skill-path KEY=PATH`. Discovery candidates do not imply every host loads every directory.

```bash
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json init --mode full --voice none --subtitles none
```

`none` means no narration; approved music/SFX may remain. Subtitles are independent. `existing` uses real approved audio; `jianying` uses the disclosed optional app route.

HyperFrames standalone installs use its documented CLI commands, including `npx hyperframes media-use resolve`. Do not call the copied legacy media-use/scripts/resolve.mjs shim or plugin-only helpers as if a full monorepo/plugin root were present. The installer uses sparse checkout for subdirectory skills; root-level projects may include larger media libraries.

The installer records the choice in `.cut-station-setup.json` beside installed skill directories, outside the skill package. On first use, read that receipt if present and match its catalog hash; reuse an explicit current decision. Pending/no record or changed source revisions require a new choice. `--reconfigure` asks again. The receipt is local setup data, not authorization for unrelated tools/services. Do not include it in a public release.

Read-only setup status: `python3 scripts/install.py --agent codex --status` (or use the same --agent/--dest as installation). This checks the current catalog fingerprint and performs no writes, downloads or prompts.
