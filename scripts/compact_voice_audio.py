#!/usr/bin/env python3
"""Assemble reviewed PCM WAV cue ranges without changing speech rate or samples.

This is a local editing fallback, not a Jianying integration. All source WAVs
must already be real decoded PCM16 at the manifest's sample rate/channels.
Ranges are reviewed by listening before use; silence detection never cuts them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import wave

from build_jianying_srt import build as build_jianying_srt


def integer(value: object, name: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def milliseconds(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a non-negative number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{name} must be finite and >= 0")
    return result


def ms_samples(value: float, sample_rate: int) -> int:
    return math.floor(value * sample_rate / 1000 + 0.5)


def atomic_text(path: Path, value: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent,
                                     prefix=f".{path.name}.", delete=False) as f:
        temporary = Path(f.name)
        f.write(value)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def assemble(manifest_path: Path, output: Path, timing_path: Path,
             srt_path: Path | None, force: bool) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    if manifest.get("script_status", "final") != "final":
        raise ValueError("only finalized script cues may be assembled; script_status must be final")
    rate = integer(manifest.get("sample_rate"), "sample_rate", 1)
    channels = integer(manifest.get("channels"), "channels", 1)
    if channels not in (1, 2):
        raise ValueError("channels must be 1 or 2")
    lead = ms_samples(milliseconds(manifest.get("lead_in_ms", 80), "lead_in_ms"), rate)
    tail = ms_samples(milliseconds(manifest.get("tail_out_ms", 120), "tail_out_ms"), rate)
    default_gap = milliseconds(manifest.get("default_gap_ms", 180), "default_gap_ms")
    max_gap = milliseconds(manifest.get("max_unannotated_gap_ms", 600),
                           "max_unannotated_gap_ms")
    cues = manifest.get("cues")
    if not isinstance(cues, list) or not cues:
        raise ValueError("cues must be a non-empty ordered array")

    srt_manifest_path = srt_path.with_suffix(".manifest.json") if srt_path else None
    if srt_path and srt_path.suffix.lower() != ".srt":
        raise ValueError("--srt output must use the .srt suffix")
    targets = [output, timing_path] + ([srt_path, srt_manifest_path] if srt_path else [])
    if len({p.resolve() for p in targets}) != len(targets):
        raise ValueError("output, timing-json and srt paths must be different")
    for target in targets:
        if target.resolve() == manifest_path.resolve():
            raise ValueError("an output may not overwrite the manifest")
        if target.exists() and not force:
            raise ValueError(f"output exists; use a new version or --force: {target}")

    seen = set()
    records = []
    pieces = []
    frame_bytes = channels * 2
    cursor = lead
    source_hashes = {}
    source_ends = {}
    for index, cue in enumerate(cues):
        if not isinstance(cue, dict):
            raise ValueError(f"cue {index + 1} must be an object")
        cue_id = cue.get("id")
        if not isinstance(cue_id, str) or not cue_id.strip() or cue_id in seen:
            raise ValueError(f"cue {index + 1} needs a non-empty unique string id")
        seen.add(cue_id)
        text = cue.get("text")
        if not isinstance(text, str) or not text.strip() or "\n\n" in text or "\r" in text:
            raise ValueError(f"cue {cue_id} needs non-empty text without blank lines/CR")
        if cue.get("range_reviewed") is not True:
            raise ValueError(f"cue {cue_id}: range_reviewed must be true after listening")
        path_value = cue.get("path")
        if not isinstance(path_value, str) or not path_value:
            raise ValueError(f"cue {cue_id} needs an audio path")
        source = (manifest_path.parent / path_value).resolve()
        if source in {p.resolve() for p in targets}:
            raise ValueError(f"output may not overwrite source audio: {source}")
        start = integer(cue.get("keep_start_sample"), f"cue {cue_id} keep_start_sample")
        end = integer(cue.get("keep_end_sample"), f"cue {cue_id} keep_end_sample", 1)
        if source in source_ends and start < source_ends[source]:
            raise ValueError(f"cue {cue_id}: ranges from the same source must be "
                             "ordered and non-overlapping; review duplicate speech")
        with wave.open(str(source), "rb") as audio:
            if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth(),
                    audio.getcomptype()) != (rate, channels, 2, "NONE"):
                raise ValueError(f"cue {cue_id}: source must be real PCM16 WAV, "
                                 f"{rate} Hz, {channels} channel(s); normalize a copy first")
            count = audio.getnframes()
            if not 0 <= start < end <= count:
                raise ValueError(f"cue {cue_id}: keep range [{start}, {end}) "
                                 f"is outside source sample count {count}")
            audio.setpos(start)
            pcm = audio.readframes(end - start)
        if len(pcm) != (end - start) * frame_bytes:
            raise ValueError(f"cue {cue_id}: truncated source PCM data")
        source_ends[source] = end
        if source not in source_hashes:
            source_hashes[source] = hashlib.sha256(source.read_bytes()).hexdigest()
        gap_ms = milliseconds(cue.get("gap_after_ms", default_gap),
                              f"cue {cue_id} gap_after_ms") if index < len(cues) - 1 else 0
        pause_note = cue.get("pause_note", "")
        if not isinstance(pause_note, str):
            raise ValueError(f"cue {cue_id}: pause_note must be text")
        if gap_ms > max_gap and not pause_note.strip():
            raise ValueError(f"cue {cue_id}: gap {gap_ms:g} ms needs pause_note "
                             f"above {max_gap:g} ms; review instead of cutting blindly")
        gap = ms_samples(gap_ms, rate)
        duration = end - start
        record = {
            "id": cue_id, "text": text,
            "sample_start": cursor, "sample_end": cursor + duration,
            "sample_count": duration,
            "start_seconds": cursor / rate,
            "end_seconds": (cursor + duration) / rate,
            "start": cursor / rate,
            "end": (cursor + duration) / rate,
            "gap_after_samples": gap, "pause_note": pause_note,
            "source": str(source),
            "source_sha256": source_hashes[source],
            "source_sample_count": count,
            "source_keep_start_sample": start,
            "source_keep_end_sample": end,
            "range_reviewed": True,
        }
        if "short_exception" in cue:
            record["short_exception"] = cue["short_exception"]
        records.append(record)
        pieces.append((pcm, gap))
        cursor += duration + gap

    total = cursor + tail
    timing = {
        "schema": "reviewed-voice-compaction/v1",
        "script_status": "final",
        "revision": manifest.get("revision") or "measured_compaction",
        "timing_source": "measured",
        "audio_source": str(output.resolve()),
        "timing_kind": "measured_pcm_samples",
        "provenance": "local assembly of reviewed exported/generated WAV cue ranges",
        "manifest": str(manifest_path.resolve()),
        "output": str(output.resolve()),
        "sample_rate": rate, "channels": channels, "sample_width_bytes": 2,
        "sample_index_unit": "audio frames: one sample per channel",
        "sample_count": total, "duration_seconds": total / rate,
        "lead_in_samples": lead, "tail_out_samples": tail,
        "speech_processing": "PCM samples copied unchanged; no tempo/pitch/fade processing",
        "cues": records,
    }
    # Validate the requested SRT before writing any output; share the same strict
    # builder and manifest format instead of maintaining a second SRT writer.
    srt_result = build_jianying_srt(timing) if srt_path else None
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix=f".{output.name}.",
                                         suffix=".wav", delete=False) as f:
            temporary = Path(f.name)
        with wave.open(str(temporary), "wb") as master:
            master.setnchannels(channels)
            master.setsampwidth(2)
            master.setframerate(rate)
            master.writeframesraw(b"\0" * lead * frame_bytes)
            for pcm, gap in pieces:
                master.writeframesraw(pcm)
                master.writeframesraw(b"\0" * gap * frame_bytes)
            master.writeframesraw(b"\0" * tail * frame_bytes)
        with wave.open(str(temporary), "rb") as check:
            if check.getnframes() != total:
                raise ValueError("written master sample count does not match cue manifest")
        temporary.replace(output)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)

    timing["master_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    atomic_text(timing_path, json.dumps(timing, ensure_ascii=False, indent=2) + "\n")
    if srt_result:
        srt, srt_manifest, _ = srt_result
        atomic_text(srt_path, srt)
        atomic_text(srt_manifest_path, json.dumps(srt_manifest, ensure_ascii=False, indent=2) + "\n")
    return {"cue_count": len(records), "sample_rate": rate, "sample_count": total,
            "duration_seconds": total / rate, "output": str(output.resolve()),
            "timing_json": str(timing_path.resolve()),
            "srt": str(srt_path.resolve()) if srt_path else None,
            "srt_manifest": str(srt_manifest_path.resolve()) if srt_manifest_path else None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timing-json", type=Path, required=True)
    parser.add_argument("--srt", type=Path)
    parser.add_argument("--force", action="store_true", help="overwrite output versions only")
    args = parser.parse_args()
    try:
        result = assemble(args.manifest.resolve(), args.output, args.timing_json,
                          args.srt, args.force)
    except (OSError, ValueError, wave.Error, EOFError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
