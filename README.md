# CutStation

Turn your screen recordings, slides, and existing voiceover into a tutorial or product demo with Codex or Claude Code. Review the script and captions first, watch a preview, then export the finished video when you're ready.

[中文说明](README.zh-CN.md)

## What you can make

| Your task | What you get |
| --- | --- |
| Make a tutorial from recordings and slides | A script to review, optional narration, an SRT synced to the voiceover when provided, an edited preview, and a finished video. Add callouts, motion, and sound effects where they help. |
| Write the script or captions first | A standalone script or SRT. Ask to review the writing before narration or editing starts. |
| Fix one thing in an existing edit | With the source project, change a caption, font, overlay, or shot while keeping approved narration and the rest of the edit in place. |

For Chinese scripts, the [hook library](assets/copywriting/library.json) gives you 364 opening patterns. Pick one, fill its ellipses with your topic, and keep the original wording around them. If you've already chosen an opening, use it as written.

## Get started

**1. Install it.** [Download or clone the repository](https://github.com/xiaocaie/cut-station). From its directory, run the command for your agent with Python 3.9 or later:

```bash
# Codex
python3 scripts/install.py --agent codex

# Claude Code
python3 scripts/install.py --agent claude-code
```

Choose the optional editing and motion skills you want to install, or reuse the ones you have. See the [installation guide](references/installation.md) for other agents and manual setup.

**2. Share your files and say what you want.** Give your agent the paths to your recordings, slides, audio, or source project. Try this:

> Use CutStation to turn these recordings and slides into a tutorial. Keep my existing voiceover and let me review the captions first. Show me a preview, then export a 1080p, 60 fps video after I approve it.

You can also ask for just the SRT, a single overlay removed, or a visual demo with the original music and no narration.

## Voiceover and export

- **Voiceover:** Use your own audio, generate narration with the Jianying desktop app, or skip narration.
- **Preview and export:** Ask your agent to check FFmpeg and your chosen renderer before the first video edit. The default export is **1920×1080, 60 fps MOV**. Ask for the editable project if you plan to make more changes. Script writing doesn't need a renderer.

[Requirements](references/agent-compatibility.md) · [Troubleshooting](references/troubleshooting.md) · [Licenses and source notices](THIRD_PARTY_NOTICES.md)
