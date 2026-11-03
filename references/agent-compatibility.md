# Agent and runtime compatibility

The portable interface is ordinary SKILL.md, relative files and Python standard-library helpers. `agents/openai.yaml` is optional UI metadata; other hosts may ignore it. Core scripts need no Codex SDK/account or native cua API. Use the host's invocation syntax.

| Environment | Supported design | Evidence limit |
| --- | --- | --- |
| Codex with files/shell | Read the skill and run helpers/selected renderer | Public release has no new full-film run; desktop capability is host-dependent |
| Claude Code with files/shell | Standard skill format and same command-line helpers | Full agent-driven film has not been tested here |
| Other coding agents | File/shell-based workflow with explicit paths | Check discovery, media access, permissions and renderer; no blanket claim |
| Chat-only interface | Text guidance/scripts/planning | No actual local rendering or export without execution tools |
| macOS with Jianying | Optional whole-text voice workflow | Requires app/version, voice access and supported desktop control or manual work |
| Windows/Linux/headless | Helpers plus a compatible selected renderer | Native Jianying automation is untested/unavailable; use manual/existing audio or skip |

Python helpers require 3.9+. Media checks require ffmpeg/ffprobe on PATH. Engine and skills-manager Node requirements are independent: inspect the pinned upstream version instead of assuming the current shell meets them. Install only the selected route's missing tools.

Translate semantic app steps to the host's actual desktop API. Do not copy cua.getApp into a host without cua. Without supported desktop access, provide a complete narration TXT and manual generation/export steps, then resume from the real audio. Do not report manual actions as automated.

Quality depends on model, materials, planning, fonts, renderer/version, voice and review. A portable skill cannot promise equally polished or pixel-identical films across agents. A frozen project/assets/toolchain can be compared deterministically; independently generated projects require independent review.

Validation levels: (1) format/reference checks; (2) helper tests and synthetic media; (3) actual engine sample; (4) real host-agent task; (5) continuous film viewing/listening. Passing one does not imply the next. Publish only observed results.
