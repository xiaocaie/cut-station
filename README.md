# CutStation

**AI video editing skill for coding agents.**

[中文说明](README.zh-CN.md)

Create source-grounded videos with scripts, optional narration, measured captions, purposeful motion and artifact-level checks. Work on a full video or just a script, subtitle file, font edit, preview or export. Protect approved work and keep a single timeline.

This is a portable workflow plus local Python helpers. It is not a bundled renderer, unlimited free TTS service or proof of equivalent output across every model/agent. The public package contains no private company examples or user footage.

## Install

Download/extract or clone this repository, then from its root:

```bash
python3 scripts/install.py --agent codex
# or
python3 scripts/install.py --agent claude-code
# another host / explicit skill root:
python3 scripts/install.py --agent generic --dest /absolute/agent/skills
```

Python 3.9+ is required. Setup asks whether to install **all four recommended projects, selected ones, or none**: HyperFrames, Video Use, Remotion Agent Skills and Video Shotcraft. HyperFrames includes its three official companion entries, shown in the prompt. Git is needed only to fetch recommendations. Selected upstream revisions are pinned in recommended-skills.json. Existing skill directories are preserved.

`--recommended none` skips downloads. `--recommended all` or `--recommended remotion,shotcraft` records an explicit choice. Agents must ask before choosing for a user. A non-interactive default leaves recommendations pending. The choice is stored locally outside the package; `--reconfigure` changes it. `--dry-run` changes nothing. This installs skill files only; it does not configure render tools, applications, keys or paid services.

You can also copy this folder to a host-recognized skills directory or use its generic skills manager. Those paths do **not** execute our interactive installer; the skill asks about recommendations on first use. Reload/rescan as your host requires. See [installation details](references/installation.md).

## Use

Ask your agent, for example:

> Use cut-station to turn these recordings into a short tutorial. Preserve the approved script, use my existing audio, and provide a preview before export.

> Use cut-station for a visual-only product demo. No narration or subtitles. Keep approved music and show the real operation result clearly.

Jianying desktop TTS is **optional**. The agent explains the installed-app/control requirement and voice/account limits before using it. You may provide audio, export manually, or skip it entirely. Other agents need their own supported desktop controls; a Codex-specific API is never assumed.

Visual production uses [computed render evidence and independent review](references/quality-gates.md). Creators submit evidence; they cannot mark their own visual work verified. Card implementation, applicable dynamic sections and all review criteria must be addressed. Machine checks do not prove aesthetics or actual listening, and review-ready is distinct from user acceptance. Partial routes do not acquire unrequested video or narration steps.

## What is portable

Standard SKILL.md + relative references; Python 3.9+ helpers; optional rendering through an available engine. FFmpeg/ffprobe are needed for media checks. Recommended tools have separate runtime and license requirements. Hosts without local files/shell cannot run local production.

Format/helper tests do not prove full-film production on Claude Code, Windows or every other agent. Full cross-agent output equivalence remains unverified. See [compatibility and evidence levels](references/agent-compatibility.md).

## Verify and contribute

```bash
python3 -m unittest discover -s tests -v
python3 scripts/release_check.py
```

On Windows use the host's Python command and set environment variables using its shell syntax. Put real project media/state outside this repository. The helper tests use synthetic fixtures and actual tiny generated media where FFmpeg is available; they do not operate Jianying or invoke paid APIs. CI configuration is included; a local pass does not mean hosted CI has run.

For changes, run tests and the offline package checker, and describe actual viewing/listening limits. Follow the [public-release guide](references/public-release.md). [MIT](LICENSE) covers original public instructions/helpers; bundled fonts retain OFL and upstream projects/assets retain their own terms. See [third-party notices](THIRD_PARTY_NOTICES.md).

## Recovery and reusable copy

The [complete hook text corpus](assets/copywriting/library.json) includes 364 patterns, 96 examples and eight methods, with source attribution and stable IDs. [Select and fill](references/copywriting-library.md) only the original ellipses; a supplied finished hook stays verbatim. Third-party source text does not inherit the code MIT license.

[Recovery and artifact paths](references/troubleshooting.md) covers actual font/crop failures, narrow overlay edits, player/export diagnosis and a relative project-index template. Confirmed per-request narration limits support evidenced semantic chunks; the default remains complete-text narration. Current-render evidence and independent review replace creator-assigned visual verified. User-directed removal of auxiliary still labels is scoped and evidence-bound.
