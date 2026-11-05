# Xiaocaie Cut Station

**Turn your footage into a finished video with Codex or Claude Code.** Give Xiaocaie Cut Station a brief and your recordings, slides, or images. Review the script, add a voiceover if you want one, and get an edited preview you can refine before export.

[简体中文](README.zh-CN.md) · [Quick start](#quick-start) · [Workflow](#workflow) · [Deliverables](#deliverables)

## Why Xiaocaie Cut Station

Writing, narration, editing, and exporting often live in separate tools. Every handoff means moving files, syncing timing, or redoing an edit. Xiaocaie Cut Station connects those steps: it carries the approved script into voiceover, aligns captions to the recorded audio, and uses a shared set of visual, editing, and export standards. Use the same workflow across a batch of tutorials or product demos for consistent results.

In a project production record, the time to make one video went from **180 minutes to about 40 minutes**, a reduction of **about 77.8%**. Time will vary with the footage, the edit, and the number of revisions.

## Quick start

### 1. Install

Clone the repository and run the command for your agent from the repository directory (Python 3.9+):

```bash
git clone https://github.com/xiaocaie/cut-station.git
cd cut-station

# Codex
python3 scripts/install.py --agent codex

# Or Claude Code
python3 scripts/install.py --agent claude-code
```

The installer lets you choose optional editing and motion skills. Reuse any you already have. Reload your agent if the skill doesn't appear. For other agents or manual setup, see the [installation guide](references/installation.md).

### 2. Give your agent a brief and your files

Attach the recordings, images, and slides, or share their local paths. Add any existing script, voiceover, or editable project you want to keep. A few sentences are enough to start:

> Use Xiaocaie Cut Station to turn these recordings and slides into a tutorial for first-time users. Lead with what they'll be able to do, then show the steps. Let me review the script first. Once I approve it, use my chosen Jianying voice, cut a preview, and export in 1080p at 60 fps after I've reviewed it.

## Workflow

| Step | What you do | What Xiaocaie Cut Station delivers |
| --- | --- | --- |
| **1 · Review the script** | Describe the video in a few sentences and share your footage, images, or slides. | A caption script you can edit, with an opening that fits the topic and narration grounded in your material. For Chinese scripts, the [hook library](assets/copywriting/library.json) has 364 opening patterns: pick a line and replace its ellipses with your topic. |
| **2 · Add a voiceover** | Approve the script and choose a Jianying voice, supply your own audio, or skip narration. Sign in only if Jianying prompts for it. | With Jianying desktop available, Xiaocaie Cut Station enters the approved script, generates the narration, and brings the exported audio back to your editing project. When audio-only MP3 export is available, it uses that file. Captions are timed to the actual voiceover. |
| **3 · Watch the first cut** | Tell the agent which moments or outcomes to show. | A playable preview from your footage, with synced captions, highlights, transitions, and motion or sound where they help explain the content. |
| **4 · Revise and export** | Give feedback by timestamp or describe what you want changed, then confirm the export specs. | An updated cut that keeps approved parts in place for targeted changes, followed by a checked final file. The default is **1080p at 60 fps (MOV)**; you can request other specs. |

## Deliverables

| If you need… | Ask for… |
| --- | --- |
| A full tutorial or product demo | A reviewable script, optional voiceover, timed SRT, playable preview, and final video. |
| Just the script or subtitles | A script draft, or an SRT timed to the supplied voiceover. |
| A change to an existing edit | The specific caption, overlay, or shot you want changed. Provide the editable source project. |
| Files to keep editing | The editable project, subtitle and narration files, and a list of source assets. |
| A series of videos | A shared visual style and export profile, with a separate preview and final file for each video. |

## Tools and requirements

For writing, you only need the skill and the source material. For editing and export, your agent needs local file and command access, FFmpeg/ffprobe, and a renderer for the chosen route. For Jianying narration, it also needs access to the desktop app; availability, voices, and export options depend on the app and account.

| Integration | Where it helps |
| --- | --- |
| [Video Use](https://github.com/browser-use/video-use) | Work with recordings and speech timing. |
| [Remotion Agent Skills](https://github.com/remotion-dev/skills) or [HyperFrames](https://github.com/heygen-com/hyperframes) | Build and render captions, overlays, and motion graphics. Choose the route that fits the project. |
| [Video Shotcraft](https://github.com/Vincentwei1021/video-shotcraft) | Select shot, transition, and sound treatments. |
| Jianying desktop | Turn approved narration text into a voice track for editing. |
| FFmpeg / ffprobe | Prepare media and check the exported file's format, dimensions, frame rate, and decoding. |

The installer sets up skill files. Install the desktop app and runtime tools only for the workflow you choose. See [agent compatibility](references/agent-compatibility.md) and [installation options](references/installation.md).

## Help and license

- Start with [Troubleshooting](references/troubleshooting.md) if a voice, font, preview, or export doesn't work.
- To report a problem, [open an issue](https://github.com/xiaocaie/cut-station/issues) with your agent, tool versions, the step that failed, and a minimal example.
- The project is [MIT licensed](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md) for bundled fonts and reference assets.
