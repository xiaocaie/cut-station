#!/usr/bin/env python3
"""Prepare one complete Jianying TTS text object, separate from display subtitles."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def prepare(document):
    if not isinstance(document, dict) or document.get("script_status") != "final":
        raise ValueError("先冻结定稿：script_status 必须为 final")
    text = document.get("narration_text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("缺少 narration_text：提供保留自然标点的完整定稿，不从碎字幕猜回口播")
    if re.search(r"\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->", text):
        raise ValueError("配音输入不得包含 SRT 时间码")
    # Only paragraph whitespace changes. Punctuation, wording and numbers survive.
    paragraph = re.sub(r"\s+", " ", text).strip()
    manifest = {
        "schema_version": 1,
        "script_status": "final",
        "revision": document.get("revision"),
        "mode": "whole_paragraph",
        "text_object_count": 1,
        "planned_generation_count": 1,
        "text": paragraph,
        "text_sha256": sha256(paragraph.encode("utf-8")),
        "character_count": len(paragraph),
        "normalization": "collapse whitespace only; preserve words and punctuation",
        "not_proven": ["UI contains exactly one text object", "TTS generation succeeded", "complete listening review"],
    }
    return paragraph, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="定稿 JSON，含 script_status=final 和 narration_text")
    parser.add_argument("output", type=Path, help="整段配音 .txt，另写 .voice-input.json")
    args = parser.parse_args()
    try:
        source = args.input.resolve()
        output = args.output.resolve()
        manifest_path = output.with_suffix(".voice-input.json")
        if output.suffix.lower() != ".txt":
            raise ValueError("输出必须为 .txt")
        if any(p.exists() for p in (output, manifest_path)) or source in (output, manifest_path):
            raise ValueError("使用新版本文件名；不覆盖源稿或已有配音输入")
        paragraph, manifest = prepare(json.loads(source.read_text(encoding="utf-8-sig")))
        manifest.update(source=str(source), source_sha256=sha256(source.read_bytes()), text_file=str(output))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(paragraph, encoding="utf-8")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"text_file": str(output), "manifest": str(manifest_path),
                          "mode": "whole_paragraph", "text_object_count": 1,
                          "character_count": len(paragraph)}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
