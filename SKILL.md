---
name: cut-station
description: Create and edit source-grounded tutorials, product demos and other videos with a coding agent. Use for scripts, optional narration, measured subtitles, screen-recording edits, motion graphics, previews and verified exports. Supports partial edits and protects approved material.
license: MIT
metadata:
  version: "0.1.0-rc.1"
---

# CutStation

Turn real footage and a clear brief into an editable, reviewable video. This is an agent workflow with local helpers, not a bundled editor or a guarantee of identical output across models.

## Startup

1. Fully read this entry, [execution protocol](references/execution-ledger.md) and [defaults](references/default-profile.md). Identify scope, project, approved version and protected files/tracks. Follow current user instructions and actual authorization.
2. On installation or first use, read [installation](references/installation.md). Offer all four recommended skill projects, selected ones, or skip; reuse existing installations and a current explicit setup receipt. Never silently install, overwrite another skill or configure a paid service. Plain skills managers do not run this package's custom installer; offer explicit setup when appropriate.
3. Before generating narration, explain: “Jianying text-to-speech is an optional desktop step. It prepares the complete script and exports a continuous audio track; a confirmed per-request character limit may require a few semantic chunks. It needs the installed app plus supported desktop access; voices/quotas depend on your account and version. You can provide audio, export manually, or skip narration.” Ask only if unresolved. A user who declined narration does not need another question; do not open the app, run TTS or request speech-service keys.
4. Check [agent compatibility](references/agent-compatibility.md). Choose `jianying`, `existing` or `none` explicitly. Subtitles are independent: `--subtitles none` supports visual-only projects. No narration can still include approved music/SFX. Without real speech, caption timing is visual/provisional, never fabricated measured speech.
5. Select only the needed [route](workflow-manifest.json): script / subtitles / voice_input / voice / full / preview / edit / font_only / export / asset_package. A preview request does not authorize full export or publication; skill maintenance does not authorize changing a video.
6. Use `scripts/workflow_guard.py` with project-local state. Choose `engine_remotion` or `engine_hyperframes` before writing engine code; add `source_processing` and `shotcraft` only when actually used and installed. Resolve optional skills through host roots or `--skill-path KEY=PATH`. Declining recommendations leaves base writing/timing/validation available. Missing an engine limits only dependent rendering; explain the gap and continue independent work.

## Production invariants

- Ground claims in actual footage/results. Distinguish real, illustrative, planned and unverified material. Do not combine unrelated cases into fabricated continuous success.
- For Chinese tutorial/promotional hooks, [fill only the original screenshot's ellipses](references/copywriting-library.md) with the concrete task requirements. Keep every other word, number and punctuation unchanged unless the user explicitly changes it. Use a user-selected finished opening verbatim; preserve approved body copy.
- Protect approved text, audio, timing and imagery. Make targeted edits. If the user asks for script review, wait for that version's approval before dependent production; otherwise do not add repeated approval gates.
- Real recordings default to 1×. Do not slow, loop or freeze/repeat frames to imply continuous operations. A 60fps label does not prove smooth playback.
- Cut after the complete object → action → result is understandable. A shot may span captions. Declared 0.5s exposure/hold is a floor, not comprehension proof.
- Jianying narration defaults to one complete punctuated text object and one generation. An explicit user/UI limit permits evidenced semantic chunks; keep the same voice/speed and join actual exports before timing. Display SRT is built after actual audio; never use sentence SRT as separate TTS clips. Reuse approved voice/speed; no second unrequested speed change.
- Display captions follow semantic units, normally at most two short sentences. Use [caption guidance](references/script-subtitles.md) for the current language. These display constraints do not split narration input.
- Read selected shot cards, exact implementations and sound attribution. Choose one main timeline. Optional skills do not justify extra ASR, duplicate pipelines or motion in protected reading sections.
- Use coherent hierarchy, typography, material and purposeful motion. Actually load fonts and check readability. Neon is an optional shared preset; current art direction takes precedence.

## Stage references

The manifest owns required packets/checks; titles and summaries do not replace full selected content.

| Stage | Read and produce |
| --- | --- |
| Sources | [SOP](references/AI视频制作SOP.md), [data contract](references/production-data-contract.md); source facts, rights, metadata and gaps |
| Script | [writing](references/internet-copywriting.md), [hook/copy selection](references/copywriting-library.md), [captions](references/script-subtitles.md); draft/final status, evidence and protections |
| Optional voice | [whole-text narration](references/jianying-voice-ai-edit.md), [UI recipe](references/jianying-ui-recipe.md); one input and actual exported audio |
| Timing/captions | Actual approved audio and measured cues, or explicitly visual/provisional timing |
| Editing | [constraints](references/production-constraints.md), [visuals](references/visual-direction.md), [QA](references/remotion-production-qa.md); source/output clocks and real preview |
| Motion/sound | [recommended skill roles](references/motion-library-workflow.md); selected cards/sources/attribution and actual event frames |
| Delivery | [export](references/export-audio-reliability.md), [delivery template](assets/交付验收与复盘模板.md); artifact evidence and remaining gaps |

For demonstrated failures or a narrowly scoped revision, read [problem recovery and artifact paths](references/troubleshooting.md). It covers voice limits, font/crop failures, local overlays, evidence scope and project indexes. Cover generation keeps its own requested style and ratio; it does not reopen the approved video.

## Execution and completion

Visual production follows the [evidence and independent-review protocol](references/quality-gates.md). Creator reports submit evidence with `status=submitted`; they cannot assign visual `verified`. Register the actual plan, compute evidence from the current render, and obtain an independent per-criterion, per-card and dynamic-section review. Missing implementation or open findings blocks exit. `review_ready` is ready for user acceptance; it is not user acceptance or proof of aesthetics from code. Scoped script/voice/subtitle/export/material-only work keeps its authorized route.

Read the execution protocol before acknowledging packets. From the skill directory, a no-narration/no-subtitles project starts with:

```bash
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json init --mode full --voice none --subtitles none
python3 scripts/workflow_guard.py --state /absolute/project/workflow.json plan --stage intake
```

For installed optional capabilities add, for example, `--features engine_remotion,shotcraft`. Explicit mapping: `--skill-path remotion=/actual/skills/remotion-best-practices/SKILL.md`. Do not acknowledge unread content or store project state inside the installed skill.

Delivery defaults: 1920×1080, 60fps, compact H.264/AAC MOV; portrait swaps dimensions. Honor explicit user/platform settings. Do not present upsampled source as native detail. Keep an editable project/source index when requested.

The guard is a **cooperative local gate**. Hashes, schemas, declared intervals and media decoding do not prove comprehension, aesthetic quality or actual viewing/listening, and cannot intercept every host tool. Report code/static checks, short playback, continuous viewing/listening and actual export separately as verified / pending / not executed / not applicable.

Only record reusable preferences when requested. Keep company files, private footage/chats, credentials and local evidence outside the package. See the [public-release guide](references/public-release.md) before publishing a modified copy.
