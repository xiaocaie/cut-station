#!/usr/bin/env python3
"""Versioned reading packets and cooperative execution gates for AI video projects.

This local helper cannot isolate the agent or intercept native CUA calls. Its
receipts/observations are agent-attested; file hashes and built-in checks are
computed. It never claims runtime-enforced authorization or comprehension.
"""

import argparse
import glob
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid
from skill_paths import resolve_skill
import quality_gate
import prepare_voice_text

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "workflow-manifest.json"


def implementation_hash():
    return digest(Path(__file__).read_bytes() + Path(quality_gate.__file__).read_bytes()
                  + quality_gate.CATALOG.read_bytes() + Path(prepare_voice_text.__file__).read_bytes())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    p = Path(path).expanduser().resolve()
    if not p.is_file() or p.stat().st_size == 0:
        raise ValueError(f"文件不存在或为空：{p}")
    return digest(p.read_bytes())


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(path, data):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def event(state, kind, **data):
    state["events"].append({"sequence": len(state["events"]) + 1,
                            "time": time.time(), "kind": kind, **data})


def resolve_doc(spec, manifest, state=None):
    spec = {"path": spec} if isinstance(spec, str) else dict(spec)
    name = spec["path"]
    if name.startswith("@"):
        state = state or {}
        legacy = manifest.get("external_skills", {}).get(name[1:])
        path = resolve_skill(name[1:], project=state.get("project"),
                             override=state.get("skill_paths", {}).get(name[1:]),
                             legacy=legacy if isinstance(legacy, str) else None)
    else:
        path = Path(name).expanduser()
        path = (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
    file_hash(path)
    return path, spec.get("sections")


def packets(state, stage, manifest):
    if stage not in state["route"]:
        raise ValueError(f"阶段不在本轮范围：{stage}")
    specs = list(manifest["core_docs"]) + list(manifest["stages"][stage]["docs"])
    for feature in state["features"]:
        item = manifest["features"][feature]
        if stage in item["stages"]:
            specs += item["docs"]
    specs += state.get("extra_docs", {}).get(stage, [])
    result, seen = [], set()
    for spec in specs:
        path, sections = resolve_doc(spec, manifest, state)
        source_hash = file_hash(path)
        selector = json.dumps(sections, ensure_ascii=False)
        if (str(path), selector) in seen:
            continue
        seen.add((str(path), selector))
        image = path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
        if image:
            chunks = [(None, None, "请用 view_image 或当前允许的图像读取工具查看此文件；路径和哈希不替代看图")]
        else:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
            selected, found, active, level = [], set(), not sections, 0
            for number, line in enumerate(lines, 1):
                heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
                if sections and heading:
                    depth, title = len(heading[1]), heading[2]
                    if title in sections:
                        active, level = True, depth
                        found.add(title)
                    elif active and depth <= level:
                        active = False
                if active:
                    selected.append((number, line))
            if sections and found != set(sections):
                raise ValueError(f"必读章节缺失：{path} {set(sections) - found}")
            chunks, group, length = [], [], 0
            for number, line in selected:
                rendered = f"{number}: {line}\n"
                if group and length + len(rendered) > 2800:
                    chunks.append((group[0][0], group[-1][0], "".join(x[1] for x in group)))
                    group, length = [], 0
                group.append((number, rendered))
                length += len(rendered)
            if group:
                chunks.append((group[0][0], group[-1][0], "".join(x[1] for x in group)))
        for start, end, content in chunks:
            key = digest((str(path) + source_hash + selector + content).encode())
            result.append({"id": key, "path": str(path), "source_sha256": source_hash,
                           "start_line": start, "end_line": end, "kind": "image" if image else "text",
                           "content": content})
    return result


def pack_signature(state, stage, manifest):
    return digest(json.dumps([p["id"] for p in packets(state, stage, manifest)]).encode())


def preserved(state):
    for item in state["protected"]:
        if file_hash(item["path"]) != item["sha256"]:
            raise ValueError(f"保护项发生改变：{item['path']}")


def fresh(state, stage, manifest):
    item = state["stages"].get(stage, {})
    expected_state = quality_gate.STAGE_STATES[stage] if quality_gate.applies(state, stage) else "verified"
    if item.get("status") != expected_state:
        raise ValueError(f"前置阶段未通过：{stage}")
    if not item.get("report_path") or not item.get("file_snapshots"):
        raise ValueError(f"阶段缺少实际出口报告：{stage}")
    if item.get("pack_signature") != pack_signature(state, stage, manifest):
        raise ValueError(f"规范版本已变化，需重新核验：{stage}")
    if item.get("implementation_sha256") != implementation_hash():
        raise ValueError(f"门禁实现已更新，需重新核验：{stage}")
    for path, expected in item.get("file_snapshots", {}).items():
        if file_hash(path) != expected:
            raise ValueError(f"阶段证据或产物变化：{stage} {path}")
    if quality_gate.applies(state, stage):
        if item.get("quality_context") != quality_gate.context_signature(state, stage):
            raise ValueError(f"质量方案/当前渲染/独立审查已换版，需重新提交阶段出口：{stage}")
        quality_gate.stage_evidence(state, stage, load(item["report_path"]))


def prerequisites(state, stage, manifest):
    preserved(state)
    for earlier in state["route"][:state["route"].index(stage)]:
        fresh(state, earlier, manifest)


def ensure_read(state, stage, manifest):
    missing = []
    for packet in packets(state, stage, manifest):
        record = state["reads"].get(packet["id"], {})
        if record.get("epoch") != state["epoch"] or not record.get("acknowledged"):
            missing.append({k: packet[k] for k in ("path", "start_line", "end_line", "kind")})
    if missing:
        raise ValueError("必读内容尚未完整返回并确认：" + json.dumps(missing, ensure_ascii=False))


def check_ready(state, stage, manifest):
    prerequisites(state, stage, manifest)
    ensure_read(state, stage, manifest)
    ids = set()
    for constraint in state.get("constraints", []):
        if not constraint.get("id") or constraint["id"] in ids or not constraint.get("requirement") or not constraint.get("stages") or any(s not in state["route"] for s in constraint["stages"]):
            raise ValueError("每条用户约束需要唯一ID、具体要求和本轮适用阶段")
        ids.add(constraint["id"])
    item = state["stages"].setdefault(stage, {})
    for rule in manifest["stages"][stage]["rules"]:
        decision = item.get("decisions", {}).get(rule, {})
        if decision.get("pack_signature") != pack_signature(state, stage, manifest):
            raise ValueError(f"缺少当前版本的规则应用决定：{rule}")
    if stage in ("voice_input", "jianying_voice"):
        lock = state.get("script_lock", {})
        if not lock or file_hash(lock["path"]) != lock["sha256"]:
            raise ValueError("配音前必须锁定当前定稿，稿件变化后需重锁")
        if state["script_review_required"] and lock.get("authority") != "user":
            raise ValueError("用户要求先审稿，缺少本版本的用户确认记录")
        if file_hash(lock["authorization_evidence"]) != lock.get("authorization_sha256"):
            raise ValueError("定稿确认依据已变化，需重新核对授权记录")
    if stage == "jianying_voice":
        inputs = state["stages"]["voice_input"].get("artifacts", [])
        if not any(a.get("role") == "voice_input" for a in inputs):
            raise ValueError("缺少单文本配音输入清单")
    return pack_signature(state, stage, manifest)


def media_info(path):
    tool = shutil.which("ffprobe")
    if not tool:
        raise ValueError("媒体检查需要 ffprobe")
    result = subprocess.run([tool, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def validate_artifact(artifact, state):
    path = Path(artifact["path"]).expanduser().resolve()
    file_hash(path)
    role = artifact.get("role", "file")
    if path.suffix.lower() == ".json":
        data = load(path)
        if role == "voice_input":
            prepare_voice_text.validate_input_files(data)
            lock = state.get("script_lock", {})
            if str(Path(data["source"]).resolve()) != lock.get("path") or data["source_sha256"] != lock.get("sha256"):
                raise ValueError("配音输入不是当前锁定稿件")
        if role == "timing":
            if data.get("timing_source") != "measured" or not data.get("audio_source"):
                raise ValueError("实测时间轴需要真实音频来源")
            audio = media_info(data["audio_source"])
            duration = float(audio["format"]["duration"])
            previous = 0
            if not data.get("cues"):
                raise ValueError("实测时间轴缺少 cues")
            for cue in data["cues"]:
                start, end = cue["start"], cue["end"]
                if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (start, end)) or not (previous <= start < end <= duration):
                    raise ValueError("实测句轴越界、重叠或时间无效")
                previous = end
        if role == "timeline":
            fps = float(data["fps"])
            if not math.isfinite(fps) or fps <= 0:
                raise ValueError("时间轴 fps 无效")
            for shot in data.get("shots", []):
                if shot.get("type") != "screen_recording":
                    continue
                source = float(shot["source_out"]) - float(shot["source_in"])
                output = float(shot["output_out"]) - float(shot["output_in"])
                rate = float(shot.get("playback_rate", 1))
                if not all(math.isfinite(v) for v in (source, output, rate)) or min(source, output) <= 0 or rate < 1 or output > source + 1 / fps + 1e-9:
                    raise ValueError("录屏存在慢放或无效区间")
    if path.suffix.lower() == ".srt":
        from validate_srt import inspect
        extra = load(artifact["manifest"]) if artifact.get("manifest") else None
        result = inspect(path.read_text(encoding="utf-8-sig"), jianying=True, manifest=extra)
        if not result["structural_valid"]:
            raise ValueError("SRT 检查失败：" + "; ".join(result["errors"]))
        if "audio_timing" in state["route"]:
            if not extra or extra.get("timing_source") != "measured" or not extra.get("audio_source"):
                raise ValueError("已有真实配音路线的最终SRT必须附实测manifest及音频来源")
            file_hash(extra["audio_source"])
    if role in ("audio", "video"):
        info = media_info(path)
        if not any(s["codec_type"] == ("audio" if role == "audio" else "video") for s in info["streams"]):
            raise ValueError("媒体缺少所声明的流")
        tool = shutil.which("ffmpeg")
        if not tool:
            raise ValueError("媒体解码检查需要 ffmpeg")
        subprocess.run([tool, "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"],
                       check=True, capture_output=True)
        if role == "video":
            expected = {**state.get("defaults", {}), **artifact.get("expected", {})}
            if "duration_seconds" not in expected:
                raise ValueError("成片产物需声明预期 duration_seconds，不能拿实际文件长度当目标")
            command = [sys.executable, str(ROOT / "scripts/validate_export.py"), str(path),
                       "--width", str(expected["width"]), "--height", str(expected["height"]),
                       "--fps", str(expected["fps"]), "--container", expected["container"],
                       "--duration-seconds", str(expected["duration_seconds"]), "--check-cadence", "--decode"]
            if expected.get("frames") is not None:
                command += ["--frames", str(expected["frames"])]
            if state.get("voice") == "none": command.append("--no-audio")
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode:
                raise ValueError("实际成片参数/PTS/解码检查失败：" + result.stdout[-3000:] + result.stderr[-500:])


def finish_stage(state, stage, report_path, manifest):
    item = state["stages"].get(stage, {})
    signature = check_ready(state, stage, manifest)
    if item.get("status") != "in_progress" or item.get("entry_signature") != signature:
        raise ValueError("必须先 enter；进入后规范变化需要重新进入")
    report = load(report_path)
    if report.get("stage") != stage:
        raise ValueError("验收报告阶段不匹配")
    checks = {x["id"]: x for x in report.get("checks", [])}
    required = list(manifest["stages"][stage]["checks"])
    required += [c["id"] for c in state.get("constraints", []) if stage in c.get("stages", [])]
    snapshots = {str(Path(report_path).resolve()): file_hash(report_path)}
    visual = quality_gate.applies(state, stage)
    for check_id in required:
        check = checks.get(check_id, {})
        submitted_state = "submitted" if visual else "verified"
        if check.get("status") != submitted_state or not check.get("evidence") or len(check.get("note", "").strip()) < 8:
            if visual and check.get("status") == "verified":
                raise ValueError("视觉阶段禁止制作方自填verified；提交证据，由程序和独立逐项审查决定")
            raise ValueError(f"缺少实际验收证据：{check_id}")
        for path in check["evidence"]:
            snapshots[str(Path(path).resolve())] = file_hash(path)
    artifacts = report.get("artifacts", [])
    for artifact in artifacts:
        validate_artifact(artifact, state)
        path = str(Path(artifact["path"]).resolve())
        snapshots[path] = file_hash(path)
        if artifact.get("manifest"):
            snapshots[str(Path(artifact["manifest"]).resolve())] = file_hash(artifact["manifest"])
        if artifact.get("role") in ("voice_input", "timing"):
            data = load(path)
            if artifact.get("role") == "voice_input":
                for target in prepare_voice_text.validate_input_files(data):
                    snapshots[str(target.resolve())] = file_hash(target)
            for key in ("text_file", "source", "audio_source"):
                if data.get(key):
                    target = str(Path(data[key]).resolve())
                    snapshots[target] = file_hash(target)
    roles = {a.get("role") for a in artifacts}
    needed_role = {"voice_input": "voice_input", "jianying_voice": "audio", "audio_timing": "timing", "srt": "srt", "rough_edit": "timeline", "export": "video"}.get(stage)
    if needed_role and needed_role not in roles:
        raise ValueError(f"缺少阶段产物：{needed_role}")
    if visual:
        snapshots.update(quality_gate.stage_evidence(state, stage, report))
    preserved(state)
    result_state = quality_gate.STAGE_STATES[stage] if visual else "verified"
    item.update(status=result_state, pack_signature=signature, file_snapshots=snapshots,
                report_path=str(Path(report_path).resolve()),
                artifacts=artifacts, implementation_sha256=implementation_hash(),
                quality_context=quality_gate.context_signature(state, stage) if visual else None)
    event(state, "stage_evaluated", stage=stage, result=result_state, report=str(Path(report_path).resolve()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init")
    p.add_argument("--mode", required=True)
    p.add_argument("--voice", choices=["jianying", "existing", "none"], required=True,
                   help="Choose after explaining optional Jianying narration to the user")
    p.add_argument("--subtitles", choices=["yes", "none"], default="yes")
    p.add_argument("--skill-path", action="append", default=[], metavar="KEY=PATH")
    p.add_argument("--features", default="")
    p.add_argument("--script-review-required", action="store_true")
    for name in ("plan", "read", "decide", "check", "enter", "exit", "run", "require"):
        p = sub.add_parser(name)
        p.add_argument("--stage", required=True)
        if name == "read": p.add_argument("--chunk", type=int, required=True)
        if name == "decide": p.add_argument("--decisions", type=Path, required=True)
        if name == "exit": p.add_argument("--report", type=Path, required=True)
        if name == "run": p.add_argument("argv", nargs=argparse.REMAINDER)
        if name == "require":
            p.add_argument("--path", required=True)
            p.add_argument("--reason", required=True)
    p = sub.add_parser("ack")
    p.add_argument("--receipt", required=True)
    p.add_argument("--end-marker", required=True)
    p.add_argument("--observation-ref", required=True)
    p = sub.add_parser("protect")
    p.add_argument("--file", type=Path, required=True)
    p = sub.add_parser("lock-script")
    p.add_argument("--file", type=Path, required=True)
    p.add_argument("--authority", choices=["user", "delegated"], required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p = sub.add_parser("revise")
    p.add_argument("--from-stage", required=True)
    p.add_argument("--reason", required=True)
    p = sub.add_parser("quality-plan")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--creator-id", required=True)
    p = sub.add_parser("quality-evidence")
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("quality-review")
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--reviewer-id", required=True)
    sub.add_parser("resume")
    sub.add_parser("summary")
    args = parser.parse_args()
    try:
        state_path = args.state.expanduser().resolve()
        if state_path.is_relative_to(ROOT):
            raise ValueError("项目状态不得写入技能安装目录")
        manifest = load(MANIFEST)
        if args.command == "init":
            if state_path.exists(): raise ValueError("状态已存在，请接续或 revise，不覆盖")
            route = manifest["routes"][args.mode].copy()
            if args.voice != "jianying":
                route = [s for s in route if s not in ("voice_input", "jianying_voice")]
            if args.voice == "none": route = [s for s in route if s != "audio_timing"]
            if args.subtitles == "none":
                if args.mode == "subtitles": raise ValueError("subtitles 模式不能同时禁用字幕")
                route = [s for s in route if s != "srt"]
            skill_paths = {}
            for mapping in args.skill_path:
                key, separator, value = mapping.partition("=")
                if not separator or key not in manifest.get("external_skills", {}) or not value:
                    raise ValueError("--skill-path 需要已知 KEY=PATH")
                skill_paths[key] = str(resolve_skill(key, override=value))
            features = [x for x in args.features.split(",") if x]
            if any(f not in manifest["features"] for f in features): raise ValueError("未知条件资料特性")
            state = {"schema_version": 3, "project": str(state_path.parent), "mode": args.mode, "voice": args.voice,
                     "enforcement": "cooperative_local_gate", "epoch": uuid.uuid4().hex,
                     "route": route, "features": features, "script_review_required": args.script_review_required,
                     "subtitles": args.subtitles, "skill_paths": skill_paths,
                     "defaults": {"width":1920,"height":1080,"fps":60,"container":"mov","display_font":"Smiley Sans"},
                     "protected": [], "constraints": [], "reads": {}, "stages": {}, "events": [], "extra_docs": {}}
            event(state, "init", mode=args.mode, voice=args.voice)
        else:
            state = load(state_path)
            if state.get("schema_version") != 3: raise ValueError("旧台账不能沿用自报视觉通过；先保留原件，为当前授权范围建立v3状态并重核相关证据")
        cmd, output = args.command, None
        if hasattr(args, "stage") and args.stage not in state["route"]: raise ValueError("阶段不在本轮范围")
        if cmd == "plan":
            output = {"stage": args.stage, "packets": [{k:v for k,v in p.items() if k != "content"} for p in packets(state,args.stage,manifest)],
                      "rules": manifest["stages"][args.stage]["rules"], "checks": manifest["stages"][args.stage]["checks"]}
        elif cmd == "read":
            pack = packets(state, args.stage, manifest)
            if not 1 <= args.chunk <= len(pack): raise ValueError("chunk 超出必读包范围")
            packet = pack[args.chunk - 1]
            receipt, marker = uuid.uuid4().hex, uuid.uuid4().hex
            source = {k:v for k,v in packet.items() if k != "content"}
            state["reads"][packet["id"]] = {"receipt": receipt, "end_marker": marker, "epoch": state["epoch"], "acknowledged": False, "source":source}
            event(state, "read_emitted", stage=args.stage, packet=packet["id"], source=source, receipt=receipt)
            output = {"packet": {k:v for k,v in packet.items() if k != "content"}, "chunk": args.chunk, "total_chunks": len(pack),
                      "content": packet["content"], "receipt": receipt, "END_READ": marker}
        elif cmd == "ack":
            records = [r for r in state["reads"].values() if r["receipt"] == args.receipt]
            if len(records) != 1 or records[0]["end_marker"] != args.end_marker or records[0]["epoch"] != state["epoch"]:
                raise ValueError("读取凭据失效或未取得完整尾标记")
            if not args.observation_ref.strip(): raise ValueError("缺少实际工具观察引用")
            records[0].update(acknowledged=True, observation_ref=args.observation_ref, trust="agent_attested")
            event(state, "read_acknowledged", receipt=args.receipt, observation_ref=args.observation_ref, trust="agent_attested")
        elif cmd == "decide":
            ensure_read(state,args.stage,manifest)
            decisions = load(args.decisions)
            if not isinstance(decisions, list): raise ValueError("decisions 必须是数组")
            target = state["stages"].setdefault(args.stage, {}).setdefault("decisions", {})
            for row in decisions:
                if row["rule"] not in manifest["stages"][args.stage]["rules"]: raise ValueError("规则不属于本阶段")
                if any(len(row.get(k, "").strip()) < 8 for k in ("action", "verification")): raise ValueError("写具体行动和验证方法，不能只写已考虑")
                target[row["rule"]] = {**row, "owner": manifest["rules"][row["rule"]]["owner"], "pack_signature": pack_signature(state,args.stage,manifest)}
            event(state, "decisions_recorded", stage=args.stage)
        elif cmd in ("check", "enter", "run"):
            signature = check_ready(state,args.stage,manifest)
            if cmd != "check":
                state["stages"].setdefault(args.stage, {}).update(status="in_progress", entry_signature=signature)
                event(state, "stage_entered", stage=args.stage)
            if cmd == "run":
                argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
                if not argv: raise ValueError("run 需要实际命令")
                save(state_path, state)
                result = subprocess.run(argv)
                event(state, "command_result", stage=args.stage, argv=argv, returncode=result.returncode)
                save(state_path, state)
                if result.returncode: raise ValueError(f"执行失败，阶段未通过：{result.returncode}")
            output = {"allowed": True, "stage": args.stage, "enforcement": "cooperative_local_gate", "exit_still_required": True}
        elif cmd == "exit": finish_stage(state,args.stage,args.report,manifest)
        elif cmd == "protect":
            path = str(args.file.resolve())
            if any(p["path"] == path for p in state["protected"]): raise ValueError("保护基线已存在，不允许重设以掩盖修改")
            state["protected"].append({"path": path, "sha256": file_hash(path)})
            event(state, "protected_baseline", path=path)
        elif cmd == "lock-script":
            data = load(args.file)
            if data.get("script_status") != "final": raise ValueError("稿件尚未定稿")
            file_hash(args.evidence)
            if state["script_review_required"] and args.authority != "user": raise ValueError("需要对应用户确认，不能自行批准")
            state["script_lock"] = {"path": str(args.file.resolve()), "sha256": file_hash(args.file),
                                    "authority": args.authority, "authorization_evidence": str(args.evidence.resolve()),
                                    "authorization_sha256": file_hash(args.evidence)}
            event(state, "script_locked", authority=args.authority)
        elif cmd == "require":
            resolve_doc(args.path,manifest,state)
            state["extra_docs"].setdefault(args.stage, []).append({"path": args.path})
            event(state, "conditional_doc_required", stage=args.stage, path=args.path, reason=args.reason)
        elif cmd == "quality-plan":
            preserved(state)
            stage = "motion_sound_plan" if "motion_sound_plan" in state["route"] else "polish"
            plan = load(args.plan)
            selected = {str(Path(card[key]).resolve()) for card in plan.get("cards", []) for key in ("card", "implementation")}
            packet_paths = {p["path"] for p in packets(state, stage, manifest)}
            if selected - packet_paths:
                raise ValueError("选定镜头卡/准确实现必须先require进本阶段并完整读取：" + ", ".join(sorted(selected - packet_paths)))
            ensure_read(state, stage, manifest)
            binding = quality_gate.design(state, args.plan, args.creator_id)
            state["quality"] = {"design": binding}
            event(state, "quality_plan_validated", plan=str(args.plan.resolve()), cards=binding["card_ids"])
            output = {"status": "plan_validated", "cards": binding["card_ids"], "not_proven": ["actual implementation", "aesthetic quality"]}
        elif cmd == "quality-evidence":
            preserved(state)
            receipt = quality_gate.collect(state, args.video, args.out)
            state["quality"]["evidence"] = receipt
            state["quality"].pop("review", None)
            event(state, "quality_evidence_computed", **receipt)
            output = {"status": "evidence_ready", **receipt, "not_proven": ["aesthetics", "actual viewing/listening"]}
        elif cmd == "quality-review":
            preserved(state)
            receipt = quality_gate.review(state, args.report, args.reviewer_id)
            state["quality"]["review"] = receipt
            event(state, "independent_quality_review_registered", **receipt)
            output = {"status": "independently_reviewed", **receipt, "not_proven": ["user acceptance", "unobserved playback/listening", "unforgeable reviewer identity"]}
        elif cmd == "revise":
            index = state["route"].index(args.from_stage)
            for stage in state["route"][index:]: state["stages"].pop(stage,None)
            if args.from_stage in ("intake", "inventory", "script", "rough_edit", "motion_sound_plan"):
                state.pop("quality", None)
            elif args.from_stage == "polish" and state.get("quality"):
                state["quality"].pop("evidence", None); state["quality"].pop("review", None)
            elif args.from_stage == "review" and state.get("quality"):
                state["quality"].pop("review", None)
            if args.from_stage in ("intake", "inventory", "script"): state.pop("script_lock",None)
            event(state, "dependent_stages_invalidated", from_stage=args.from_stage, reason=args.reason)
        elif cmd == "resume":
            state["epoch"] = uuid.uuid4().hex
            event(state, "context_resumed")
        if cmd == "summary":
            results = []
            for stage in state["route"]:
                try:
                    prerequisites(state,stage,manifest)
                    fresh(state,stage,manifest)
                    status, reason = state["stages"][stage]["status"], ""
                except ValueError as exc: status, reason = "pending_or_stale", str(exc)
                results.append({"stage":stage,"status":status,"reason":reason})
            output = {"enforcement":"cooperative_local_gate", "stages":results,
                      "not_proven":["runtime interception of all tools", "agent comprehension", "actual viewing/listening beyond attached observations"]}
        save(state_path,state)
        print(json.dumps(output if output is not None else {"ok":True,"command":cmd},ensure_ascii=False,indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"allowed":False,"error":str(exc)},ensure_ascii=False),file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
