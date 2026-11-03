# 0.1.0-rc.1 — public release candidate

Prepared on 2026-11-03. The confirmed name is CutStation, with skill identifier cut-station and subtitle AI video editing skill. The name is not a claim of an exclusive or cleared brand.

## Included changes

- Neutral public identity and standard skill entry; separate host UI metadata.
- Explicit recommendation installer: ask/all/selected/skip, no silent non-interactive consent, no overwrite of existing skills, local choice receipt and reconfiguration.
- Four pinned upstream projects; HyperFrames core companions are installed together. Subdirectory projects use filtered sparse checkout; upstream tools/accounts/paid services are not configured.
- Cross-host skill discovery and explicit path mapping.
- Optional disclosed Jianying narration, existing/manual audio routes, independent no-narration and no-caption switches.
- Private company cases/media, internal document/chat links, historical personal evidence and unlicensed reference screenshots excluded. Public data contract rewritten independently.
- Font license/hash checks, offline package scanner, README in English/Chinese, license/notices, ignore rules and CI configuration.

## Actual validation

- 36 local helper tests passed on macOS with Python 3.9.6 and installed FFmpeg/ffprobe.
- Independent actual setup runs covered interactive decline, non-interactive pending, rerun, preservation of user changes, setup receipt reuse/reconfiguration and a custom skills root.
- HyperFrames, Video Use and Remotion skill files were actually downloaded into isolated test directories. HyperFrames's filtered sparse installation matched the full checkout file-for-file; required local Markdown links resolved. Remotion nested references were present.
- A synthetic nine-stage no-narration/no-caption flow completed, including a real tiny generated video, container/cadence/decode checks. Synthetic read acknowledgements exercised gate behavior; they did not prove a model read/understood production documents.
- Offline package checks, font/license hashes and the skill-creator format validator passed.

## Still unverified

Complete Shotcraft media-library installation; a real selected-engine composition; a real non-Codex host-agent production run; Windows/Linux execution; hosted CI execution; Jianying UI on a fresh environment; actual full-film viewing/listening and cross-agent quality equivalence.

No real user footage was uploaded, no desktop narration or paid service was invoked, and no GitHub repository was created/published by this preparation.
