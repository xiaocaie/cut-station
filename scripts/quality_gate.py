"""Evidence-bound visual gates. Computed evidence is separate from reviewer judgment.

This is still a cooperative local gate, not a sandbox or proof of honest identity.
It rejects bare success flags, missing coverage, stale renders and creator-only reviews.
"""
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "quality-requirements.json"
VISUAL_MODES = {"full", "preview", "edit", "font_only"}
STAGE_STATES = {"motion_sound_plan": "plan_validated", "polish": "evidence_ready",
                "review": "independently_reviewed", "export": "technical_verified",
                "delivery": "review_ready"}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    p = Path(path).expanduser().resolve()
    if not p.is_file() or not p.stat().st_size:
        raise ValueError(f"质量证据不存在或为空：{p}")
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fingerprint(paths):
    return {str(Path(p).expanduser().resolve()): sha(p) for p in paths}


def unchanged(snapshots):
    for path, expected in snapshots.items():
        if sha(path) != expected:
            raise ValueError(f"质量证据对应的文件已变化：{path}")


def applies(state, stage):
    return state.get("mode") in VISUAL_MODES and stage in STAGE_STATES


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"无效数字：{label}")
    return value


def design(state, plan_path, creator):
    if not creator or len(creator.strip()) < 3:
        raise ValueError("需要实际制作方标识")
    p = Path(plan_path).resolve()
    plan = load(p)
    if plan.get("schema_version") != 1:
        raise ValueError("质量方案必须使用 schema_version=1，不接受旧版自由文字方案")
    timeline = load(plan["timeline"])
    fps = number(timeline["fps"], "fps")
    shots = timeline.get("shots", [])
    if fps <= 0 or not shots:
        raise ValueError("质量方案缺少真实镜头时间轴")
    shot_map, cursor = {}, 0
    for s in shots:
        key = s.get("shot_id")
        start, end = number(s["output_in"], "output_in"), number(s["output_out"], "output_out")
        if not key or key in shot_map or start < 0 or abs(start-cursor) > 1/fps or end <= start:
            raise ValueError("镜头ID重复、存在空洞或镜头时间无效")
        if s.get("type") == "screen_recording":
            rate = number(s.get("playback_rate", 1), "playback_rate")
            if rate != 1 or abs((s["source_out"]-s["source_in"])-(end-start)) > 1/fps+1e-8:
                raise ValueError("实录必须保持1x并与真实源时钟一致")
        shot_map[key], cursor = s, end
    timing = load(plan["timing"]) if plan.get("timing") else {"cues": []}
    if state.get("subtitles") != "none" and not timing.get("cues"):
        raise ValueError("显示字幕路线缺少已锁定的cue时间轴")
    previous = 0
    for cue in timing.get("cues", []):
        start, end = number(cue["start"], "cue start"), number(cue["end"], "cue end")
        if not previous <= start < end <= cursor:
            raise ValueError("字幕cue必须有序、不重叠且位于当前成片时间范围内")
        previous = end
    sources = plan.get("source_files", [])
    if not sources:
        raise ValueError("必须绑定实际引擎源码和素材文件")
    cards = plan.get("cards", [])
    card_map, conditional, implementations = {}, [], set()
    for c in cards:
        key = c.get("id")
        if not key or key in card_map or c.get("adoption") != "implemented":
            raise ValueError("镜头卡必须有唯一ID并明确落实；candidate/partial不计入覆盖")
        for k in ("card", "implementation"):
            conditional.append(c[k]); sha(c[k])
        implementation_key = (sha(c["card"]), sha(c["implementation"]))
        if implementation_key in implementations:
            raise ValueError("重复复制同一卡片/准确实现不能冒充多种镜头卡")
        implementations.add(implementation_key)
        code = c.get("code_files", [])
        if not code or not set(map(str, map(Path, code))).issubset(set(map(str, map(Path, sources)))):
            raise ValueError("镜头卡必须映射到本期已绑定的实际引擎代码")
        if not c.get("preserved_parameters") or not c.get("adaptations"):
            raise ValueError("镜头卡缺少保留参数或实际适配记录")
        card_map[key] = c
    sections = plan.get("sections", [])
    seen, used, section_ids, override_evidence = [], set(), set(), []
    for s in sections:
        if not s.get("id") or s["id"] in section_ids:
            raise ValueError("主段ID缺失或重复")
        section_ids.add(s["id"])
        if len(s.get("purpose", "").strip()) < 8 or not s.get("shot_ids"):
            raise ValueError("每个主段必须有信息任务和对应镜头")
        seen.extend(s["shot_ids"])
        if any(x not in shot_map for x in s["shot_ids"]):
            raise ValueError("主段引用不存在的镜头")
        motion = s.get("motion")
        if motion == "library":
            if not s.get("card_ids") or any(x not in card_map for x in s["card_ids"]):
                raise ValueError("动效主段缺少已实现的准确镜头卡")
            used.update(s["card_ids"])
        elif motion in ("real_recording", "static_reading"):
            if len(s.get("quiet_reason", "").strip()) < 12:
                raise ValueError("实录/静止阅读段必须说明当前任务为什么保持安静")
            if motion == "real_recording" and any(shot_map[x].get("type") != "screen_recording" for x in s["shot_ids"]):
                raise ValueError("不能把静态贴图标成实录来规避动效覆盖")
        else:
            raise ValueError("不能用未分类或通用fade替代主段动效设计")
        start, end = min(shot_map[x]["output_in"] for x in s["shot_ids"]), max(shot_map[x]["output_out"] for x in s["shot_ids"])
        settled = number(s.get("settled_at", start), "settled_at")
        if settled < start or settled > end-load(CATALOG)["limits"]["minimum_settled_seconds"]:
            raise ValueError("主段未留出至少0.5秒落定阅读；复杂内容仍需独立判断")
        override = s.get("still_label_override")
        if override is not None:
            if (not s.get("still") or not isinstance(override, dict)
                    or override.get("authority") != "user"
                    or not isinstance(override.get("instruction"), str)
                    or len(override.get("instruction", "").strip()) < 8
                    or not override.get("evidence")):
                raise ValueError("删除静帧标识须保留still身份并附用户明确指令和依据文件")
            sha(override["evidence"])
            override_evidence.append(override["evidence"])
        if s.get("still") and not s.get("visible_still_label") and override is None:
            raise ValueError("说明静帧必须有成片可见标识，或绑定用户明确删除该标识的覆盖依据")
    if set(seen) != set(shot_map) or len(seen) != len(shot_map):
        raise ValueError("全片镜头未逐一归属主段，或重复归属")
    minimum = load(CATALOG)["limits"]["full_min_distinct_implemented_cards"]
    if state.get("mode") in ("full", "preview") and (len(used) < minimum or len([s for s in sections if s["motion"] == "library"]) < 2):
        raise ValueError("完整制作必须落实多种镜头卡并覆盖多个适用主段；单标题卡不通过")
    bound = [p, CATALOG, plan["timeline"], *sources, *conditional, *override_evidence]
    if plan.get("timing"): bound.append(plan["timing"])
    bound += [x["path"] for x in state.get("protected", [])]
    return {"creator_id": creator.strip(), "plan_path": str(p), "plan_sha256": sha(p),
            "snapshots": fingerprint(bound), "fps": fps, "duration_seconds": cursor,
            "shot_ids": list(shot_map), "section_ids": sorted(section_ids), "card_ids": sorted(used),
            "catalog_sha256": sha(CATALOG)}


def expected_frames(plan, fps, count):
    timeline = load(plan["timeline"])
    frames = {0, count-1}
    for s in timeline["shots"]:
        a, b = round(s["output_in"]*fps), round(s["output_out"]*fps)
        frames.update([a, (a+b)//2, b-1])
        if a: frames.add(a-1)
    for s in plan["sections"]:
        f = round(s["settled_at"]*fps)
        frames.update([max(0, f-1), f, min(count-1, f+1)])
    if plan.get("timing"):
        for c in load(plan["timing"])["cues"]:
            frames.add(round((c["start"]+c["end"])*fps/2))
    return sorted(f for f in frames if 0 <= f < count)


def frame_select_expression(frames):
    """Keep exact sample membership without a deep, flat additive parse tree."""
    if not frames:
        raise ValueError("真实取帧缺少必需帧号")
    def grouped(start, end):
        if end-start == 1:
            return f"eq(n\\,{frames[start]})"
        middle = (start+end)//2
        return "(" + grouped(start, middle) + "+" + grouped(middle, end) + ")"
    return grouped(0, len(frames))


def collect(state, video, output):
    binding = state.get("quality", {}).get("design")
    if not binding:
        raise ValueError("先登记并核验本期质量方案")
    unchanged(binding["snapshots"])
    path, out = Path(video).resolve(), Path(output).resolve()
    if out.exists():
        raise ValueError("质量证据目录必须是新目录，禁止覆盖旧轮证据")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise ValueError("实际取帧需要ffmpeg和ffprobe")
    probe = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-count_frames", "-show_format", "-show_streams", "-of", "json", str(path)]))
    stream = next((s for s in probe["streams"] if s["codec_type"] == "video"), None)
    if not stream:
        raise ValueError("当前质量证据必须绑定真实视频")
    fps, count = binding["fps"], round(binding["duration_seconds"]*binding["fps"])
    a, b = map(int, stream["avg_frame_rate"].split("/"))
    if b == 0 or abs(a/b-fps) > .001 or int(stream.get("nb_read_frames", 0)) != count or abs(float(stream.get("duration", probe["format"]["duration"]))-count/fps) > 1/fps+.02:
        raise ValueError("实际渲染的fps/时长与当前时间轴不一致")
    plan = load(binding["plan_path"])
    selected = expected_frames(plan, fps, count)
    out.mkdir(parents=True)
    expression = frame_select_expression(selected)
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-vf", "select="+expression,
                        "-fps_mode", "passthrough", str(out/"frame_%05d.png")], check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        raise ValueError(f"FFmpeg真实取帧失败（退出码{exc.returncode}，预期{len(selected)}帧）：" + stderr[-4000:].strip()) from exc
    actual = sorted(out.glob("frame_*.png"))
    if len(actual) != len(selected):
        raise ValueError("真实视频取帧数量不足，不能用缺帧证据放行")
    records = [{"frame": f, "path": str(p), "sha256": sha(p)} for f, p in zip(selected, actual)]
    package = {"schema_version": 1, "receipt": uuid.uuid4().hex, "plan_sha256": binding["plan_sha256"],
               "catalog_sha256": sha(CATALOG), "video": str(path), "video_sha256": sha(path),
               "fps": fps, "frames": count, "probe": probe, "images": records,
               "snapshots": {**binding["snapshots"], **fingerprint([path, *actual])},
               "trust": "computed_files_and_decoded_frames", "not_proven": ["aesthetics", "actual viewing/listening", "truth of reviewer identity"]}
    package_path = out/"package.json"
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return {"path": str(package_path), "sha256": sha(package_path), "receipt": package["receipt"]}


def evidence(state):
    q = state.get("quality", {})
    binding, receipt = q.get("design"), q.get("evidence")
    if not binding or not receipt:
        raise ValueError("缺少程序从当前视频生成的质量证据；普通文件/verified文字无效")
    unchanged(binding["snapshots"])
    if sha(receipt["path"]) != receipt["sha256"]:
        raise ValueError("取帧证据包被改动")
    package = load(receipt["path"])
    if package["receipt"] != receipt["receipt"] or package["plan_sha256"] != binding["plan_sha256"] or package["catalog_sha256"] != sha(CATALOG):
        raise ValueError("取帧证据不是当前方案/当前规则")
    unchanged(package["snapshots"])
    expected = expected_frames(load(binding["plan_path"]), binding["fps"], package["frames"])
    if [x["frame"] for x in package["images"]] != expected:
        raise ValueError("证据包未覆盖每个镜头、cue中点和切换边界")
    return package


def section_ranges(plan, fps):
    shots = {s["shot_id"]: s for s in load(plan["timeline"])["shots"]}
    return {s["id"]: (round(min(shots[x]["output_in"] for x in s["shot_ids"])*fps),
                      round(max(shots[x]["output_out"] for x in s["shot_ids"])*fps))
            for s in plan["sections"]}


def frame_observation(row, frames, label):
    if len(row.get("observation", "").strip()) < 20 or not row.get("frames") or any(type(f) is not int or f not in frames for f in row["frames"]):
        raise ValueError(label + "必须有具体画面观察及当前真实帧号")


def review(state, report_path, reviewer):
    package = evidence(state)
    binding = state["quality"]["design"]
    if not reviewer or reviewer.strip().casefold() == binding["creator_id"].strip().casefold():
        raise ValueError("制作方不能给自己注册独立审查通过")
    report = load(report_path)
    if report.get("reviewer_id") != reviewer or report.get("evidence_receipt") != package["receipt"]:
        raise ValueError("独立审查必须绑定实际审查者及当前证据凭据")
    required = set(load(CATALOG)["review_criteria"])
    rows = report.get("criteria", [])
    if len(rows) != len(required) or {x.get("id") for x in rows} != required:
        raise ValueError("独立审查缺项、重复或自创了验收标准")
    frames = {x["frame"] for x in package["images"]}
    for r in rows:
        if r.get("result") != "pass":
            raise ValueError(f"验收项尚未落实/未审/有问题：{r.get('id')}")
        frame_observation(r, frames, "审查结论")
    plan = load(binding["plan_path"])
    ranges = section_ranges(plan, binding["fps"])
    # Every claimed implementation is checked in its actual section. Distinct IDs
    # in a creator's design do not establish that a rendered card was implemented.
    expected = {(s["id"], c) for s in plan["sections"] if s["motion"] == "library" for c in s["card_ids"]}
    implementations = report.get("card_implementation", [])
    if len(implementations) != len(expected) or {(r.get("section_id"), r.get("card_id")) for r in implementations} != expected:
        raise ValueError("独立审查必须逐主段、逐镜头卡核对实际实现，不能只引用卡名")
    for r in implementations:
        if r.get("result") != "implemented":
            raise ValueError("候选、部分借鉴或未落实的镜头卡不能通过")
        a, b = ranges[r["section_id"]]
        frame_observation(r, {f for f in frames if a <= f < b}, "镜头卡实现对照")
    coverage = report.get("playback", {})
    needed = {s["id"] for s in plan["sections"] if s["motion"] in ("library", "real_recording")}
    observations = coverage.get("dynamic_samples", [])
    covered = set()
    for o in observations:
        key = o.get("section_id")
        if key not in ranges or type(o.get("start_frame")) is not int or type(o.get("end_frame")) is not int:
            raise ValueError("动态观察区间无效")
        a, b = ranges[key]
        if not a <= o["start_frame"] < o["end_frame"] <= b:
            raise ValueError("动态观察区间必须位于所声明的实际主段，不能移用其他段的观察")
        if len(o.get("tool_observation", "").strip()) < 12:
            raise ValueError("动态主段缺少实际播放观察引用")
        if o["start_frame"] == a and o["end_frame"] == b:
            covered.add(key)
    if not needed.issubset(covered):
        raise ValueError("镜头动效/真实操作未完整动态抽检对应主段，不能只用静帧或一帧通过")
    inherited_snapshots = {}
    for k in ("continuous_visual", "continuous_audio"):
        status = coverage.get(k)
        if status not in ("observed", "not_executed", "inherited_unchanged"):
            raise ValueError("必须分开记录连续观看和连续听审的真实范围")
        if status != "not_executed":
            details = coverage.get(k + "_evidence", {})
            if type(details.get("start_frame")) is not int or details["start_frame"] != 0 or type(details.get("end_frame")) is not int or details["end_frame"] != package["frames"] or len(details.get("tool_observation", "").strip()) < 12:
                raise ValueError("连续视听声明必须有当前全片范围及真实观察引用")
            if status == "inherited_unchanged":
                prior = details.get("inherited_from")
                if not prior or not details.get("unchanged_files"):
                    raise ValueError("继承未变视听结果必须绑定原观察及未变源文件")
                unchanged(details["unchanged_files"])
                if any(package["snapshots"].get(str(Path(path).resolve())) != value for path, value in details["unchanged_files"].items()):
                    raise ValueError("继承文件必须属于当前实际渲染绑定且哈希相同的文件")
                media = str(Path(details.get("media_path", "")).resolve())
                if details["unchanged_files"].get(media) != package["snapshots"].get(media) or media not in details["unchanged_files"]:
                    raise ValueError("继承视听结果必须明确绑定当前未变的实际媒体文件")
                if k == "continuous_visual" and media != package["video"]:
                    raise ValueError("新画面不能继承其他视频的连续观看结果")
                if k == "continuous_audio":
                    info = json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-of","json",media]))
                    if not any(s["codec_type"] == "audio" for s in info["streams"]):
                        raise ValueError("继承听审必须绑定含真实声音流的媒体")
                inherited_snapshots.update({str(Path(path).resolve()):value for path,value in details["unchanged_files"].items()})
                inherited_snapshots[str(Path(prior).resolve())] = sha(prior)
    if not isinstance(report.get("open_findings"), list) or report["open_findings"]:
        raise ValueError("必须明确记录未关闭问题清单；仍有问题不能注册审查通过")
    return {"path": str(Path(report_path).resolve()), "sha256": sha(report_path), "reviewer_id": reviewer,
            "evidence_receipt": package["receipt"], "scope": "independent_frames_and_declared_playback",
            "continuous_visual": coverage["continuous_visual"], "continuous_audio": coverage["continuous_audio"],
            "inherited_snapshots": inherited_snapshots}


def context_signature(state, stage):
    """Bind a stage exit to exactly the design/render/review version it used."""
    quality = state.get("quality", {})
    keys = ["design"]
    if stage != "motion_sound_plan": keys.append("evidence")
    if stage in ("review", "export", "delivery"): keys.append("review")
    payload = {k: quality.get(k) for k in keys}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def stage_evidence(state, stage, report):
    """Return computed snapshots; no caller-supplied success state is authoritative."""
    q = state.get("quality", {})
    binding = q.get("design")
    if not binding:
        raise ValueError("缺少质量方案登记，不能靠verified放行视觉阶段")
    unchanged(binding["snapshots"])
    # Recompute coverage, including mandatory distinct cards, instead of trusting cached totals.
    design(state, binding["plan_path"], binding["creator_id"])
    snapshots = dict(binding["snapshots"])
    if stage != "motion_sound_plan":
        package = evidence(state)
        snapshots.update(package["snapshots"])
        snapshots[q["evidence"]["path"]] = q["evidence"]["sha256"]
    if stage in ("review", "export", "delivery"):
        registered = q.get("review")
        if not registered or registered["evidence_receipt"] != q["evidence"]["receipt"] or sha(registered["path"]) != registered["sha256"]:
            raise ValueError("缺少当前渲染的独立逐项审查；旧报告或制作方声明无效")
        review(state, registered["path"], registered["reviewer_id"])
        snapshots[registered["path"]] = registered["sha256"]
        unchanged(registered.get("inherited_snapshots", {}))
        snapshots.update(registered.get("inherited_snapshots", {}))
    if stage in ("export", "delivery"):
        videos = [a for a in report.get("artifacts", []) if a.get("role") == "video"]
        if (stage == "export" and not videos) or any(sha(v["path"]) != package["video_sha256"] for v in videos):
            raise ValueError("导出/交付视频不是独立审查所看的当前视频")
    return snapshots
