# CutStation · 剪辑站

把你的录屏、PPT 和已有旁白交给 Codex 或 Claude Code，剪成一条软件教程、产品演示或讲解视频。你可以先看脚本、改字幕，再看预览；确认后再导出成片。

[English](README.md)

## 你可以用它做什么

| 你想做 | 你能拿到 |
| --- | --- |
| 有录屏和 PPT，想做一条完整教程 | 可审核的口播稿、配音（可选）、SRT 字幕（有旁白时按实际声音对齐）、剪辑预览和成片。可以加重点标注、动效和音效。 |
| 先把文案或字幕做好 | 单独交脚本或 SRT。你说先审稿，就等你确认后再配音或剪辑。 |
| 已经剪好了，只想改一处 | 有原工程时，可以只改指定的字幕、字体、提示文字或片段，保留已经确认的配音和其他内容。 |

开头不知道怎么写，可以从[钩子库](assets/copywriting/library.json)的 364 条句式里选一条，只把省略号换成你的内容。你已经定好的开头，直接沿用。

## 开始使用

**1. 安装。** [下载仓库](https://github.com/xiaocaie/cut-station)或克隆后，在仓库目录里运行与你的 Agent 对应的命令（需要 Python 3.9+）：

```bash
# Codex
python3 scripts/install.py --agent codex

# Claude Code
python3 scripts/install.py --agent claude-code
```

安装时可以选装推荐的剪辑和动效 skills，已有的不用重装。其他 Agent 和手动安装方式见[安装说明](references/installation.md)。

**2. 给素材，说清楚交付要求。** 把录屏、PPT、旁白文件或原工程的路径发给 Agent，再告诉它想做什么。可以直接复制这句话：

> 用 CutStation 把这个文件夹里的录屏和 PPT 剪成一条组会汇报教程。沿用已有旁白，字幕先给我审。确认后再剪，先给我看预览，通过后导出 1080p、60 帧的视频。

只需要其中一步，也可以直接说「只交 SRT 字幕」「只删右上角这句提示，其他保持原样」或「不要配音，保留原音乐」。

## 配音和导出怎么选

- **配音**：可以用你现有的音频，也可以用剪映桌面端生成。只做画面时，直接说不需要配音。
- **预览和成片**：首次剪视频时，让 Agent 检查 FFmpeg 和选用的渲染工具是否可用。未指定格式时，默认导出 **1920×1080、60fps 的 MOV**。想以后自己接着剪，可以一并要可编辑工程。只写脚本时不用准备渲染工具。

[使用条件](references/agent-compatibility.md) · [遇到问题](references/troubleshooting.md) · [许可与素材来源](THIRD_PARTY_NOTICES.md)
