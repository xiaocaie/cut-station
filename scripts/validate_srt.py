#!/usr/bin/env python3
"""Read-only SRT checks; --jianying adds the narration subtitle profile."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import unicodedata


TIME = r"(\d{2,}):(\d{2}):(\d{2}),(\d{3})"
TIMING = re.compile(r"^" + TIME + r"\s+-->\s+" + TIME + r"$")
TERMINAL_QUOTES = "\"'”’」』】）》 "


def milliseconds(parts):
    hours, minutes, seconds, millis = map(int, parts)
    if minutes >= 60 or seconds >= 60:
        raise ValueError("分钟或秒必须小于60")
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis


def visible_length(text):
    """Count visible letters/digits, not punctuation or spaces; a heuristic, not semantics."""
    return sum(character.isalnum() for character in text)


def body_sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def inspect(text, duration_seconds=None, allow_terminal_punctuation=False, commas_only=False,
            jianying=False, manifest=None, min_chars=5, max_chars=30):
    # Keep the original four positional arguments and legacy commas-only behavior.
    errors = []
    warnings = []
    normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks = re.split(r"\n[ \t]*\n+", normalized) if normalized else []
    previous_end = None
    last_end = 0
    parsed_count = 0
    manifests = {}
    if manifest is not None:
        if not isinstance(manifest, dict) or not isinstance(manifest.get("cues"), list):
            errors.append("manifest必须是包含cues数组的对象")
        else:
            for cue in manifest["cues"]:
                if not isinstance(cue, dict) or type(cue.get("index")) is not int:
                    errors.append("manifest每条字幕必须有整数index")
                    continue
                if cue["index"] in manifests:
                    errors.append(f"manifest存在重复index {cue['index']}")
                manifests[cue["index"]] = cue
            if set(manifests) != set(range(1, len(blocks) + 1)):
                errors.append("manifest的字幕index必须与SRT逐条一致")
            if manifest.get("timing_source") == "provisional":
                warnings.append("时间为待配音校时的建议版，不得声称与真实朗读同步")
    if not blocks:
        errors.append("字幕文件为空")
    for position, block in enumerate(blocks, 1):
        lines = block.splitlines()
        label = f"第{position}块"
        if len(lines) < 3:
            errors.append(f"{label}缺少序号、时间行或字幕正文")
            continue
        if lines[0].strip() != str(position):
            errors.append(f"{label}序号应为{position}，实际为{lines[0].strip()!r}")
        match = TIMING.fullmatch(lines[1].strip())
        if not match:
            errors.append(f"{label}时间格式应为HH:MM:SS,mmm --> HH:MM:SS,mmm")
            continue
        try:
            start = milliseconds(match.groups()[:4])
            end = milliseconds(match.groups()[4:])
        except ValueError as exc:
            errors.append(f"{label}{exc}")
            continue
        parsed_count += 1
        if end <= start:
            errors.append(f"{label}结束时间必须晚于开始时间")
        if previous_end is not None and start < previous_end:
            errors.append(f"{label}与前面的字幕重叠或时间倒序")
        previous_end = max(previous_end or 0, end)
        last_end = max(last_end, end)
        if duration_seconds is not None and end > duration_seconds * 1000 + 1:
            errors.append(f"{label}结束时间超出指定视频时长")
        body = "\n".join(lines[2:]).strip()
        visible = re.sub(r"<[^>]*>", "", body).strip()
        if not visible:
            errors.append(f"{label}字幕正文为空")
        terminal = visible.rstrip(TERMINAL_QUOTES)
        if not allow_terminal_punctuation and terminal.endswith(("，", "。", ",", ".")):
            errors.append(f"{label}句末含逗号或句号，不符合当前默认格式")
        if commas_only:
            prose = re.sub(r"(?<=\d)\.(?=\d)", "", visible)
            if re.search(r"[。！？.!?；;：:、…“”‘’「」『』（）()【】\[\]《》]", prose):
                errors.append(f"{label}含逗号以外的正文标点；本期需保留的术语标点应另行人工核对")
            if visible.count("，") + visible.count(",") > 1:
                errors.append(f"{label}含多于一个逗号，请按单个语义单元拆分")
        if jianying:
            cue_manifest = manifests.get(position, {})
            if cue_manifest and cue_manifest.get("text_sha256") != body_sha256(body):
                errors.append(f"{label}与manifest定稿文本不一致，例外说明不能沿用")
            if cue_manifest and (cue_manifest.get("start_ms"), cue_manifest.get("end_ms")) != (start, end):
                errors.append(f"{label}与manifest时间不一致，请从同一份实测时间数据重建")
            if "<" in body or ">" in body:
                errors.append(f"{label}含标签或尖括号，请使用剪映纯文本字幕")
            # Keep a decimal point in e.g. 1.2倍; ?/! are allowed only at the end.
            prose = re.sub(r"(?<=\d)\.(?=\d)", "", visible)
            prose = re.sub(r"[！？!?]+$", "", prose)
            if re.search(r"[。！？.!?；;：:、…“”‘’「」『』（）()【】\[\]《》]", prose):
                errors.append(f"{label}含不适用的正文标点；句中仅保留一个必要逗号，问号或叹号只放句末")
            comma_count = visible.count("，") + visible.count(",")
            if comma_count > 1:
                errors.append(f"{label}超过两短句，请人工按语义拆分")
            if terminal and unicodedata.category(terminal[-1]).startswith("P") and terminal[-1] not in "！？!?":
                errors.append(f"{label}句末只允许问号或叹号")
            if any(not part.strip() for part in re.split(r"[，,]", visible)):
                errors.append(f"{label}逗号前后必须都有完整短句")
            count = visible_length(visible)
            exception = cue_manifest.get("short_exception")
            if exception is not None and (not isinstance(exception, str) or not exception.strip()):
                errors.append(f"{label}短句例外必须填写具体原因")
            if count < min_chars and not (isinstance(exception, str) and exception.strip()):
                errors.append(f"{label}仅{count}个可见字母/数字，过短；请合并或在manifest按ID说明例外")
            if count > max_chars:
                errors.append(f"{label}有{count}个可见字母/数字，超过{max_chars}；请人工拆成适中短句")
            if len(lines[2:]) > 2:
                errors.append(f"{label}超过两行，请先修订文案与换行")
        elif len(lines[2:]) > 2:
            warnings.append(f"{label}超过两行，请按实际字号与画幅复查可读性")
    return {
        "structural_valid": not errors,
        "profile": "jianying" if jianying else "legacy",
        "block_count": len(blocks),
        "parsed_timing_count": parsed_count,
        "last_end_seconds": last_end / 1000,
        "duration_limit_seconds": duration_seconds,
        "errors": errors,
        "warnings": warnings,
        "not_checked": ["画面与旁白同步", "术语及数字准确性", "语义断句及两短句是否自然", "前三秒痛点钩子", "结尾引导", "实际字体布局"],
    }


def positive_finite(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("视频时长必须是大于0的有限数字")
    return number


def positive_integer(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("字数必须是大于0的整数")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("srt", type=Path)
    parser.add_argument("--duration-seconds", type=positive_finite)
    parser.add_argument("--allow-terminal-punctuation", action="store_true",
                        help="旧版格式明确允许句末逗号或句号时使用；不覆盖--jianying")
    parser.add_argument("--commas-only", action="store_true", help="保留旧行为：只允许必要逗号；该旧模式也会拒绝问号和叹号")
    parser.add_argument("--jianying", action="store_true", help="检查新版口播字幕：两短句、适中字数、句末只允许问号或叹号")
    parser.add_argument("--manifest", type=Path, help="构建脚本输出的manifest；包含稳定ID、文本哈希与短句例外原因")
    parser.add_argument("--min-chars", type=positive_integer, default=5, help="仅用于--jianying，默认5；4字及更短需明确例外")
    parser.add_argument("--max-chars", type=positive_integer, default=30, help="仅用于--jianying，默认30；人工视内容调整")
    args = parser.parse_args()
    if args.commas_only and args.jianying:
        parser.error("--commas-only是旧版严格模式，不能与允许问号/叹号的--jianying合用")
    if args.min_chars > args.max_chars:
        parser.error("--min-chars不能大于--max-chars")
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig")) if args.manifest else None
        report = inspect(args.srt.read_text(encoding="utf-8-sig"), args.duration_seconds,
                         args.allow_terminal_punctuation, args.commas_only,
                         args.jianying, manifest, args.min_chars, args.max_chars)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report = {"structural_valid": False, "errors": [str(exc)]}
    report["file"] = str(args.srt.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["structural_valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
