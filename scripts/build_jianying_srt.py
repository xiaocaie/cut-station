#!/usr/bin/env python3
"""Build UTF-8/CRLF Jianying SRT from finalized cues, preserving human sentence splits."""

import argparse
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import math
from pathlib import Path
import sys

from validate_srt import body_sha256, inspect, visible_length


def to_ms(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{field}必须是以秒计的有限数字")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{field}必须是以秒计的有限数字") from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f"{field}必须是非负有限秒数")
    return int((number * 1000).to_integral_value(rounding=ROUND_HALF_UP))


def timestamp(ms):
    seconds, millis = divmod(ms, 1000)
    minutes, second = divmod(seconds, 60)
    hour, minute = divmod(minutes, 60)
    return f"{hour:02d}:{minute:02d}:{second:02d},{millis:03d}"


def build(document, *, allow_provisional=False, cps=5.0, gap_ms=120, min_chars=5, max_chars=30):
    if not isinstance(document, dict):
        raise ValueError("输入必须是JSON对象")
    if document.get("script_status") != "final":
        raise ValueError('script_status必须为"final"；先完成文案交互与定稿，不把草稿直接送配音')
    source = document.get("timing_source")
    if source not in ("measured", "provisional"):
        raise ValueError('timing_source必须为"measured"或"provisional"')
    if source == "provisional" and not allow_provisional:
        raise ValueError("建议时间需要显式--allow-provisional；导出后仍须按实测配音重建")
    cues = document.get("cues")
    if not isinstance(cues, list) or not cues:
        raise ValueError("cues必须是非空数组")
    if not math.isfinite(cps) or cps <= 0 or gap_ms < 0 or min_chars <= 0 or max_chars < min_chars:
        raise ValueError("字速、间隔与字数参数无效")
    if any(not isinstance(cue, dict) for cue in cues):
        raise ValueError("每条cue必须是对象")
    timed = ["start" in cue or "end" in cue for cue in cues]
    if any(timed) and not all(timed):
        raise ValueError("时间不得部分填写；每条同时提供start/end，或全部留空生成建议时间")
    if source == "measured" and not all(timed):
        raise ValueError("实测版每条都必须提供start/end秒数")
    estimated = not any(timed)
    manifest = {
        "schema_version": 1,
        "script_status": "final",
        "revision": document.get("revision"),
        "timing_source": source,
        "timing_estimated_by_builder": estimated,
        "timing_note": "待配音校时，建议时间不能作为实测同步证据" if source == "provisional" else "调用方声明为实测；仍需听审核验",
        "audio_source": document.get("audio_source"),
        "encoding": "UTF-8 without BOM",
        "line_endings": "CRLF",
        "cues": [],
    }
    blocks = []
    ids = set()
    cursor = 0
    for index, cue in enumerate(cues, 1):
        cue_id = cue.get("id")
        if not isinstance(cue_id, str) or not cue_id.strip() or cue_id in ids:
            raise ValueError(f"第{index}条id必须是非空且不重复的稳定字符串")
        ids.add(cue_id)
        text = cue.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{cue_id}缺少定稿text")
        if text != text.strip() or "\r" in text or "\n\n" in text:
            raise ValueError(f"{cue_id}含首尾空白、CR或空行；请在定稿文本中显式整理")
        if estimated:
            start = cursor
            end = start + max(1200, round(visible_length(text) / cps * 1000))
            cursor = end + gap_ms
        else:
            if "start" not in cue or "end" not in cue:
                raise ValueError(f"{cue_id}必须同时提供start和end")
            start = to_ms(cue["start"], f"{cue_id}.start")
            end = to_ms(cue["end"], f"{cue_id}.end")
        entry = {"index": index, "id": cue_id, "text_sha256": body_sha256(text),
                 "start_ms": start, "end_ms": end}
        if "short_exception" in cue:
            entry["short_exception"] = cue["short_exception"]
        manifest["cues"].append(entry)
        blocks.append(f"{index}\n{timestamp(start)} --> {timestamp(end)}\n{text}")
    srt = "\n\n".join(blocks) + "\n"
    report = inspect(srt, jianying=True, manifest=manifest, min_chars=min_chars, max_chars=max_chars)
    if not report["structural_valid"]:
        raise ValueError("定稿字幕未通过检查：\n" + "\n".join(report["errors"]))
    manifest["validation_limits"] = {"min_chars": min_chars, "max_chars": max_chars}
    return srt.replace("\n", "\r\n"), manifest, report


def positive_float(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("必须是大于0的有限数字")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="定稿口播JSON；字段见references/script-subtitles.md")
    parser.add_argument("output", type=Path, help="输出.srt；建议时间版文件名应带待配音校时")
    parser.add_argument("--allow-provisional", action="store_true", help="允许建议时间；无start/end时才按字速估算")
    parser.add_argument("--cps", type=positive_float, default=5.0, help="仅用于未提供时间的建议版，可见字母/数字每秒，默认5")
    parser.add_argument("--gap-ms", type=int, default=120, help="仅用于估算建议时间的句间隔，默认120ms")
    parser.add_argument("--min-chars", type=int, default=5)
    parser.add_argument("--max-chars", type=int, default=30)
    parser.add_argument("--overwrite", action="store_true", help="有意覆盖同名SRT和manifest；保留已批准版本后使用")
    args = parser.parse_args()
    manifest_path = args.output.with_suffix(".manifest.json")
    try:
        if args.output.suffix.lower() != ".srt":
            raise ValueError("输出文件必须使用.srt后缀")
        if not args.overwrite and (args.output.exists() or manifest_path.exists()):
            raise ValueError("输出已存在；使用新版本文件名，或保留旧版后显式--overwrite")
        document = json.loads(args.input.read_text(encoding="utf-8-sig"))
        srt, manifest, report = build(document, allow_provisional=args.allow_provisional,
                                      cps=args.cps, gap_ms=args.gap_ms,
                                      min_chars=args.min_chars, max_chars=args.max_chars)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(srt.encode("utf-8"))
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"srt": str(args.output.resolve()), "manifest": str(manifest_path.resolve()),
                          "timing_source": manifest["timing_source"], "cue_count": report["block_count"],
                          "warnings": report["warnings"]}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
