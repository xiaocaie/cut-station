"""Synthetic local fixtures; these tests never operate Jianying or claim real reads/listening."""

import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import workflow_guard as guard
import quality_gate as quality
import prepare_voice_text as voice


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state_file = self.root / "workflow.json"
        self.manifest = guard.load(guard.MANIFEST)
        self.call("init", "--mode", "font_only", "--voice", "existing")

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, *args, expected=0):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(sys, "argv", ["workflow_guard", "--state", str(self.state_file), *map(str, args)]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = guard.main()
        self.assertEqual(code, expected, err.getvalue() + out.getvalue())
        return json.loads(out.getvalue()) if code == 0 else json.loads(err.getvalue())

    def state(self):
        return guard.load(self.state_file)

    def fixture_reads(self, stage):
        # Synthetic delivery acknowledgements exercise the gate, not an Agent's cognition.
        state = self.state()
        for packet in guard.packets(state, stage, self.manifest):
            state["reads"][packet["id"]] = {"epoch":state["epoch"], "acknowledged":True,
                                             "receipt":"synthetic", "end_marker":"synthetic", "trust":"test_fixture"}
        guard.save(self.state_file, state)

    def ready(self, stage):
        self.fixture_reads(stage)
        path = self.root / f"{stage}-decisions.json"
        guard.save(path, [{"rule":rule,"action":"按合成测试范围执行当前阶段并保留所有指定保护项", "verification":"使用实际测试文件与状态检查当前阶段出口和保护哈希"}
                          for rule in self.manifest["stages"][stage]["rules"]])
        self.call("decide", "--stage", stage, "--decisions", path)

    def finish(self, stage, artifacts=None):
        self.ready(stage)
        self.call("enter", "--stage", stage)
        evidence = self.root / f"{stage}-observation.txt"
        evidence.write_text("合成测试观察，只验证门禁和文件状态，不声称真实UI或听审", encoding="utf-8")
        report = self.root / f"{stage}-report.json"
        guard.save(report, {"stage":stage,"checks":[{"id":key,"status":"submitted" if quality.applies(self.state(), stage) else "verified", "note":"本项使用合成测试证据验证文件及阶段状态的门禁逻辑", "evidence":[str(evidence)]}
                                                    for key in self.manifest["stages"][stage]["checks"]],
                            "artifacts":artifacts or []})
        self.call("exit", "--stage", stage, "--report", report)

    def quality_fixture(self, mode=None, library=True, collect=True):
        """Real synthetic render plus clearly test-only reading/reviewer fixtures."""
        if mode:
            self.state_file.unlink()
            self.call("init", "--mode", mode, "--voice", "none", "--subtitles", "none")
        self.plan_path = self.root / "quality-plan.json"
        self.timeline_path = self.root / "quality-timeline.json"
        self.engine = self.root / "engine.js"
        self.engine.write_text("export const syntheticGateExercise = frame => frame / 60;", encoding="utf-8")
        guard.save(self.timeline_path, {"fps":30,"shots":[
            {"shot_id":"one","type":"motion_graphic","output_in":0,"output_out":1},
            {"shot_id":"two","type":"motion_graphic","output_in":1,"output_out":2}]})
        cards = []
        sections = []
        stage = "motion_sound_plan" if "motion_sound_plan" in self.state()["route"] else "polish"
        for i, shot in enumerate(("one", "two")):
            section = {"id":shot, "purpose":"Isolated synthetic gate behavior exercise", "shot_ids":[shot], "settled_at":i+.2}
            if library:
                card = self.root / f"card-{shot}.md"
                implementation = self.root / f"implementation-{shot}.js"
                card.write_text(f"# Recipe {shot}\n" + f"Synthetic complete recipe {shot}\n" * 250, encoding="utf-8")
                implementation.write_text(f"export const {shot} = frame => frame / {i+1};", encoding="utf-8")
                for path in (card, implementation):
                    self.call("require", "--stage", stage, "--path", path, "--reason", "Selected synthetic source for gate behavior test")
                cards.append({"id":shot,"adoption":"implemented","card":str(card),"implementation":str(implementation),
                              "code_files":[str(self.engine)],"preserved_parameters":"Synthetic timing relationship preserved", "adaptations":"Test-sized isolated implementation fixture"})
                section.update(motion="library",card_ids=[shot])
            else:
                section.update(motion="static_reading",quiet_reason="Only typography is changed; preserve existing static source composition")
            sections.append(section)
        plan = {"schema_version":1,"timeline":str(self.timeline_path),"source_files":[str(self.engine)],"cards":cards,"sections":sections}
        if self.state().get("subtitles") != "none":
            timing = self.root / "preserved-visual-cues.json"
            guard.save(timing,{"timing_source":"provisional","cues":[{"start":0,"end":1,"text":"Synthetic visual cue"},{"start":1,"end":2,"text":"Preserved second cue"}]})
            plan["timing"] = str(timing)
        guard.save(self.plan_path, plan)
        self.fixture_reads(stage)
        self.call("quality-plan", "--plan", self.plan_path, "--creator-id", "synthetic-creator")
        self.video = self.root / "synthetic-render.mp4"
        subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i","testsrc2=size=64x64:rate=30:duration=2", "-an","-c:v","libx264",str(self.video)],check=True,capture_output=True)
        if collect:
            self.call("quality-evidence", "--video", self.video, "--out", self.root / "evidence")

    def review_fixture(self):
        package = quality.evidence(self.state())
        plan = guard.load(self.plan_path)
        ranges = quality.section_ranges(plan,30)
        return {"reviewer_id":"synthetic-independent-reviewer", "evidence_receipt":package["receipt"],
                "criteria":[{"id":key,"result":"pass", "observation":"Synthetic observation for exercising evidence schema; no aesthetic acceptance is claimed.", "frames":[0,30]}
                            for key in quality.load(quality.CATALOG)["review_criteria"]],
                "card_implementation":[{"section_id":section["id"],"card_id":card,"result":"implemented", "observation":"Synthetic fixture compares implementation to the selected recipe in its actual section.", "frames":[ranges[section["id"]][0]]}
                                       for section in plan["sections"] if section["motion"] == "library" for card in section["card_ids"]],
                "playback":{"dynamic_samples":[{"section_id":key,"start_frame":a,"end_frame":b,"tool_observation":"Synthetic dynamic observation for testing only; no real playback claimed."} for key,(a,b) in ranges.items()],
                            "continuous_visual":"not_executed","continuous_audio":"not_executed"}, "open_findings":[]}

    def register_review(self, report=None, expected=0):
        self.review_path = self.root / "quality-review.json"
        guard.save(self.review_path, report if report is not None else self.review_fixture())
        return self.call("quality-review", "--report", self.review_path, "--reviewer-id", "synthetic-independent-reviewer", expected=expected)

    def test_unread_gate_prevents_command_side_effect(self):
        marker = self.root / "must-not-exist"
        self.call("run", "--stage", "intake", "--", sys.executable, "-c", f"open({str(marker)!r},'w').write('bad')", expected=1)
        self.assertFalse(marker.exists())

    def test_cannot_decide_before_reading(self):
        path = self.root / "decisions.json"
        guard.save(path, [{"rule":"SCOPE","action":"先写一个足够长的行动但是没有读取资料","verification":"检查输出内容与文件但是仍然缺少阅读证据"}])
        self.call("decide", "--stage", "intake", "--decisions", path, expected=1)

    def test_missing_tail_ack_rejected(self):
        result = self.call("read", "--stage", "intake", "--chunk", "1")
        recorded = self.state()["reads"][result["packet"]["id"]]["source"]
        self.assertEqual(recorded["source_sha256"],guard.file_hash(recorded["path"]))
        self.assertIsInstance(recorded["start_line"],int)
        self.call("ack", "--receipt", result["receipt"], "--end-marker", "truncated", "--observation-ref", "synthetic tool output", expected=1)
        self.call("ack", "--receipt", result["receipt"], "--end-marker", result["END_READ"], "--observation-ref", "synthetic tool output")
        self.call("enter", "--stage", "intake", expected=1)  # Other chunks are still missing.

    def test_reading_without_application_decision_is_insufficient(self):
        self.fixture_reads("intake")
        self.call("enter", "--stage", "intake", expected=1)

    def test_legal_batch_runs_but_does_not_mark_exit_passed(self):
        self.ready("intake")
        marker = self.root / "executed"
        self.call("run", "--stage", "intake", "--", sys.executable, "-c", f"open({str(marker)!r},'w').write('ok')")
        self.assertEqual(marker.read_text(encoding="utf-8"), "ok")
        self.assertEqual(self.state()["stages"]["intake"]["status"], "in_progress")

    def test_missing_dependency_blocks_downstream_command(self):
        self.ready("polish")
        self.call("enter", "--stage", "polish", expected=1)

    def test_protected_file_change_blocks(self):
        path = self.root / "audio.wav"
        path.write_bytes(b"original-source")
        self.call("protect", "--file", path)
        self.ready("intake")
        path.write_bytes(b"changed-source")
        self.call("enter", "--stage", "intake", expected=1)
        self.call("protect", "--file", path, expected=1)

    def test_evidence_change_invalidates_dependencies_and_summary(self):
        self.finish("intake")
        self.assertEqual(self.call("summary")["stages"][0]["status"], "verified")
        (self.root / "intake-observation.txt").write_text("证据已被修改", encoding="utf-8")
        self.ready("polish")
        self.call("enter", "--stage", "polish", expected=1)
        self.assertEqual(self.call("summary")["stages"][0]["status"], "pending_or_stale")

    def test_changed_required_document_needs_reread_and_new_decision(self):
        path = self.root / "selected-source.md"
        path.write_text("# 真实测试条件资料\n按当前版本执行", encoding="utf-8")
        self.call("require", "--stage", "intake", "--path", path, "--reason", "本轮实际采用的条件资料")
        self.ready("intake")
        path.write_text("# 真实测试条件资料\n规范已经修改", encoding="utf-8")
        self.call("enter", "--stage", "intake", expected=1)
        self.fixture_reads("intake")
        self.call("enter", "--stage", "intake", expected=1)

    def test_resume_requires_current_packet_again(self):
        self.ready("intake")
        self.call("resume")
        self.call("enter", "--stage", "intake", expected=1)

    def test_voice_requires_correct_version_user_confirmation(self):
        # Focus this test on the actual voice-input gate using synthetic upstream exits.
        state = self.state()
        state.update(route=["intake","script","voice_input"], mode="voice", script_review_required=True)
        guard.save(self.state_file,state)
        self.finish("intake")
        self.finish("script")
        script, authorization = self.root / "script.json", self.root / "approval.txt"
        guard.save(script,{"script_status":"final","narration_text":"这是完整的定稿。"})
        authorization.write_text("合成测试的用户确认记录，仅供门禁回归", encoding="utf-8")
        self.call("lock-script", "--file",script,"--authority","delegated","--evidence",authorization,expected=1)
        self.ready("voice_input")
        self.call("enter","--stage","voice_input",expected=1)
        self.call("lock-script", "--file",script,"--authority","user","--evidence",authorization)
        self.call("enter","--stage","voice_input")
        guard.save(script,{"script_status":"final","narration_text":"用户改了这一版定稿。"})
        self.call("enter","--stage","voice_input",expected=1)

    def test_local_font_route_has_no_voice_or_export(self):
        self.assertEqual(self.state()["route"],["intake","polish","review","delivery"])
        self.call("enter","--stage","jianying_voice",expected=1)

    def test_exit_without_real_evidence_cannot_pass(self):
        self.ready("intake")
        self.call("enter","--stage","intake")
        report = self.root / "empty-report.json"
        guard.save(report,{"stage":"intake","checks":[{"id":"scope_and_protected","status":"verified","note":"声称已经完成但没有任何真实证据文件","evidence":[]}],"artifacts":[]})
        self.call("exit","--stage","intake","--report",report,expected=1)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_legal_font_route_finishes_with_sources_unchanged(self):
        audio = self.root / "original-audio.bin"
        audio.write_bytes(b"preserved-voice")
        self.call("protect","--file",audio)
        self.quality_fixture(library=False)
        self.finish("intake")
        self.finish("polish")
        self.register_review()
        self.finish("review")
        self.finish("delivery")
        statuses = {x["stage"]:x["status"] for x in self.call("summary")["stages"]}
        self.assertEqual(statuses, {"intake":"verified", "polish":"evidence_ready", "review":"independently_reviewed", "delivery":"review_ready"})
        self.assertEqual(audio.read_bytes(),b"preserved-voice")

    def test_conditional_document_is_in_execution_packet(self):
        path = self.root / "actual-demo.py"
        path.write_text("def demo():\n    return 'actual implementation'\n", encoding="utf-8")
        self.call("require","--stage","polish","--path",path,"--reason","本期选择的准确实现")
        plan = self.call("plan","--stage","polish")
        self.assertTrue(any(p["path"] == str(path.resolve()) for p in plan["packets"]))

    def test_slow_recording_rejected_from_actual_mapping(self):
        path = self.root / "timeline.json"
        guard.save(path,{"fps":60,"shots":[{"type":"screen_recording","source_in":0,"source_out":10,"output_in":0,"output_out":10,"playback_rate":0.99}]})
        with self.assertRaises(ValueError): guard.validate_artifact({"path":str(path),"role":"timeline"},self.state())
        guard.save(path,{"fps":60,"shots":[{"type":"screen_recording","source_in":0,"source_out":10,"output_in":0,"output_out":11}]})
        with self.assertRaises(ValueError): guard.validate_artifact({"path":str(path),"role":"timeline"},self.state())

    def test_bad_subtitles_and_fake_audio_rejected(self):
        srt = self.root / "bad.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\n四字碎片\n", encoding="utf-8")
        with self.assertRaises(ValueError): guard.validate_artifact({"path":str(srt),"role":"srt"},self.state())
        audio = self.root / "fake.wav"
        audio.write_text("this is not audio", encoding="utf-8")
        with self.assertRaises((ValueError,subprocess.SubprocessError)):
            guard.validate_artifact({"path":str(audio),"role":"audio"},self.state())

    def test_measured_timing_requires_real_audio_and_ranges(self):
        audio = self.root / "source.wav"
        with wave.open(str(audio),"wb") as w:
            w.setparams((1,2,48000,0,"NONE","not compressed"))
            w.writeframes(b"\x00\x00" * 48000)
        path = self.root / "timing.json"
        guard.save(path,{"timing_source":"provisional","audio_source":str(audio),"cues":[{"start":0,"end":0.5}]})
        with self.assertRaises(ValueError): guard.validate_artifact({"path":str(path),"role":"timing"},self.state())
        guard.save(path,{"timing_source":"measured","audio_source":str(audio),"cues":[{"start":0,"end":2}]})
        with self.assertRaises(ValueError): guard.validate_artifact({"path":str(path),"role":"timing"},self.state())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_real_video_container_and_cadence_are_checked(self):
        video = self.root / "actual.mp4"
        subprocess.run([shutil.which("ffmpeg"),"-v","error","-f","lavfi","-i","color=c=blue:s=64x64:r=30:d=0.2", "-an","-c:v","libx264",str(video)],check=True,capture_output=True)
        state = self.state()
        state["voice"] = "none"
        expected = {"width":64,"height":64,"fps":30,"duration_seconds":0.2,"frames":6,"container":"mp4"}
        guard.validate_artifact({"path":str(video),"role":"video","expected":expected},state)
        renamed = self.root / "renamed.mov"
        video.rename(renamed)
        with self.assertRaises(ValueError):
            guard.validate_artifact({"path":str(renamed),"role":"video","expected":{**expected,"container":"mov"}},state)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_full_and_preview_visual_routes_use_computed_states_without_voice(self):
        for mode in ("full", "preview"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                original_root, original_state = self.root, self.state_file
                self.root = Path(tmp); self.state_file = self.root / "workflow.json"
                self.call("init", "--mode", mode, "--voice", "none", "--subtitles", "none")
                self.quality_fixture()
                for stage in self.state()["route"]:
                    if stage == "review": self.register_review()
                    artifacts = []
                    if stage == "rough_edit": artifacts = [{"path":str(self.timeline_path),"role":"timeline"}]
                    if stage == "export": artifacts = [{"path":str(self.video),"role":"video", "expected":{"width":64,"height":64,"fps":30,"frames":60,"duration_seconds":2,"container":"mp4"}}]
                    self.finish(stage, artifacts)
                statuses = {x["stage"]:x["status"] for x in self.call("summary")["stages"]}
                self.assertEqual(statuses["delivery"], "review_ready")
                self.assertEqual(statuses["motion_sound_plan"], "plan_validated")
                self.assertEqual(statuses["polish"], "evidence_ready")
                self.assertEqual(statuses["review"], "independently_reviewed")
                self.assertEqual("export" in statuses, mode == "full")
                if mode == "full": self.assertEqual(statuses["export"], "technical_verified")
                for stage in ("voice_input", "jianying_voice", "audio_timing", "srt"): self.assertNotIn(stage,statuses)
                self.root, self.state_file = original_root, original_state

    def test_visual_creator_verified_without_quality_is_rejected(self):
        self.finish("intake")
        self.ready("polish")
        self.call("enter", "--stage", "polish")
        evidence = self.root / "bare.txt"; evidence.write_text("Bare arbitrary evidence exists",encoding="utf-8")
        report = self.root / "bare.json"
        for status in ("verified", "submitted"):
            guard.save(report,{"stage":"polish","checks":[{"id":"visual_and_protection","status":status,"note":"Creator says the entire composition looks good", "evidence":[str(evidence)]}],"artifacts":[]})
            self.call("exit","--stage","polish","--report",report,expected=1)
        self.assertEqual(self.state()["stages"]["polish"]["status"],"in_progress")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_selected_recipe_needs_all_current_chunks(self):
        self.quality_fixture(mode="preview")
        stage = "motion_sound_plan"
        state = self.state()
        recipe = str(Path(guard.load(self.plan_path)["cards"][0]["card"]).resolve())
        packets = [p for p in guard.packets(state,stage,self.manifest) if p["path"] == recipe]
        self.assertGreater(len(packets),1)
        state["reads"].pop(packets[-1]["id"])
        guard.save(self.state_file,state)
        self.call("quality-plan","--plan",self.plan_path,"--creator-id","synthetic-creator",expected=1)
        self.fixture_reads(stage)
        Path(recipe).write_text(Path(recipe).read_text()+"Changed source recipe",encoding="utf-8")
        self.call("quality-plan","--plan",self.plan_path,"--creator-id","synthetic-creator",expected=1)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_single_or_partial_card_cannot_pass_full_coverage(self):
        self.quality_fixture(mode="preview")
        plan = guard.load(self.plan_path)
        for mutate in (lambda p:p["cards"][0].update(adoption="partial"),
                       lambda p:p["sections"][1].update(card_ids=["one"])):
            changed = json.loads(json.dumps(plan)); mutate(changed)
            candidate = self.root / "insufficient-plan.json"; guard.save(candidate,changed)
            with self.assertRaises(ValueError): quality.design(self.state(),candidate,"creator")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_independent_review_requires_current_each_card_and_real_section_ranges(self):
        self.quality_fixture(mode="preview")
        report = self.review_fixture()
        with self.assertRaises(ValueError): quality.review(self.state(),self.plan_path,"synthetic-creator")
        for mutation in (lambda r:r.pop("card_implementation"),
                         lambda r:r["card_implementation"][1].update(result="partial"),
                         lambda r:r["card_implementation"][1].update(frames=[0]),
                         lambda r:r["playback"]["dynamic_samples"][1].update(start_frame=0,end_frame=1),
                         lambda r:r["playback"]["dynamic_samples"][0].update(end_frame=1),
                         lambda r:r["playback"].update(continuous_visual="observed"),
                         lambda r:r["criteria"][0].update(frames=[True]),
                         lambda r:r.update(open_findings=["Unresolved actual issue"]),
                         lambda r:r["criteria"][0].update(result="unreviewed")):
            changed = json.loads(json.dumps(report)); mutation(changed)
            self.register_review(changed,expected=1)
        self.register_review(report)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_stale_source_render_and_review_are_rejected(self):
        self.quality_fixture(mode="preview")
        self.register_review()
        original = self.engine.read_bytes(); self.engine.write_bytes(original+b" changed")
        with self.assertRaises(ValueError): quality.evidence(self.state())
        self.engine.write_bytes(original)
        original = self.video.read_bytes(); self.video.write_bytes(original+b" changed")
        with self.assertRaises(ValueError): quality.evidence(self.state())
        self.video.write_bytes(original)
        self.review_path.write_text(self.review_path.read_text()+" ",encoding="utf-8")
        with self.assertRaises(ValueError): quality.stage_evidence(self.state(),"review",{})

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_new_evidence_receipt_invalidates_old_stage_exit(self):
        self.quality_fixture(library=False)
        self.finish("intake"); self.finish("polish")
        self.assertEqual(self.call("summary")["stages"][1]["status"],"evidence_ready")
        self.call("quality-evidence","--video",self.video,"--out",self.root/"new-evidence")
        self.assertEqual(self.call("summary")["stages"][1]["status"],"pending_or_stale")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_export_rejects_unreviewed_render_even_with_same_metadata(self):
        self.quality_fixture(mode="full"); self.register_review()
        another = self.root / "different-render.mp4"
        subprocess.run(["ffmpeg","-v","error","-f","lavfi","-i","color=c=red:s=64x64:r=30:d=2","-an","-c:v","libx264",str(another)],check=True,capture_output=True)
        with self.assertRaises(ValueError):
            quality.stage_evidence(self.state(),"export",{"artifacts":[{"path":str(another),"role":"video"}]})

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_edit_and_full_delivery_bind_declared_video_to_reviewed_render(self):
        for mode in ("edit", "full"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                original_root, original_state = self.root, self.state_file
                self.root = Path(tmp); self.state_file = self.root / "workflow.json"
                try:
                    self.call("init", "--mode", mode, "--voice", "none", "--subtitles", "none")
                    self.quality_fixture()
                    candidate = self.root / "different-valid-delivery.mp4"
                    subprocess.run(["ffmpeg","-v","error","-f","lavfi","-i","color=c=red:s=64x64:r=30:d=2", "-an","-c:v","libx264",str(candidate)],check=True,capture_output=True)
                    expected = {"width":64,"height":64,"fps":30,"frames":60,"duration_seconds":2,"container":"mp4"}
                    for stage in self.state()["route"][:-1]:
                        if stage == "review": self.register_review()
                        artifacts = []
                        if stage == "rough_edit": artifacts = [{"path":str(self.timeline_path),"role":"timeline"}]
                        if stage == "export": artifacts = [{"path":str(self.video),"role":"video","expected":expected}]
                        self.finish(stage,artifacts)
                    self.ready("delivery"); self.call("enter","--stage","delivery")
                    observation = self.root / "delivery-observation.txt"
                    observation.write_text("Synthetic delivery binding fixture, no actual aesthetic or listening acceptance.",encoding="utf-8")
                    report = {"stage":"delivery","checks":[{"id":key,"status":"submitted","note":"Submit actual declared files for the current reviewed render", "evidence":[str(observation)]} for key in self.manifest["stages"]["delivery"]["checks"]],
                              "artifacts":[{"path":str(candidate),"role":"video","expected":expected}]}
                    report_path = self.root / "delivery-candidate-report.json"; guard.save(report_path,report)
                    self.assertNotEqual(quality.sha(candidate),quality.evidence(self.state())["video_sha256"])
                    self.call("exit","--stage","delivery","--report",report_path,expected=1)
                    self.assertEqual(self.state()["stages"]["delivery"]["status"],"in_progress")
                    self.assertEqual(self.call("summary")["stages"][-1]["status"],"pending_or_stale")
                    report["artifacts"][0]["path"] = str(self.video); guard.save(report_path,report)
                    self.call("exit","--stage","delivery","--report",report_path)
                    self.assertEqual(self.call("summary")["stages"][-1]["status"],"review_ready")
                finally:
                    self.root, self.state_file = original_root, original_state

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_new_plan_context_invalidates_old_plan_exit_with_old_files_intact(self):
        self.quality_fixture(mode="preview")
        for stage in ("intake","inventory","script","rough_edit","motion_sound_plan"):
            self.finish(stage,[{"path":str(self.timeline_path),"role":"timeline"}] if stage == "rough_edit" else [])
        self.assertEqual(self.call("summary")["stages"][4]["status"],"plan_validated")
        replacement = guard.load(self.plan_path); replacement["sections"][0]["purpose"] += " Updated current information task"
        new_plan = self.root / "new-plan.json"; guard.save(new_plan,replacement)
        self.call("quality-plan","--plan",new_plan,"--creator-id","synthetic-creator")
        self.assertEqual(self.call("summary")["stages"][4]["status"],"pending_or_stale")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_updated_catalog_cannot_reuse_old_frame_package(self):
        self.quality_fixture(mode="preview")
        catalog = quality.load(quality.CATALOG); catalog["review_criteria"]["composition"]["requirement"] += " Changed current requirement"
        new_catalog = self.root / "updated-catalog.json"; guard.save(new_catalog,catalog)
        with patch.object(quality,"CATALOG",new_catalog), self.assertRaises(ValueError): quality.evidence(self.state())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_cue_outside_video_cannot_be_silently_omitted_from_coverage(self):
        self.quality_fixture(mode="preview")
        plan = guard.load(self.plan_path)
        cues = self.root / "bad-cues.json"; guard.save(cues,{"cues":[{"start":4,"end":5}]})
        plan["timing"] = str(cues)
        candidate = self.root / "bad-cue-plan.json"; guard.save(candidate,plan)
        with self.assertRaises(ValueError): quality.design(self.state(),candidate,"creator")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_inherited_observation_must_bind_current_media_and_stay_unchanged(self):
        self.quality_fixture(library=False)
        report = self.review_fixture(); prior = self.root / "prior-observation.txt"
        prior.write_text("Synthetic previous observation fixture; not a claim of actual continuous viewing.",encoding="utf-8")
        media = str(self.video.resolve())
        report["playback"]["continuous_visual"] = "inherited_unchanged"
        report["playback"]["continuous_visual_evidence"] = {"start_frame":0,"end_frame":60,"tool_observation":"Synthetic unchanged observation schema exercise only", "inherited_from":str(prior), "media_path":media, "unchanged_files":{media:quality.sha(media)}}
        self.register_review(report)
        prior.write_text("Changed prior observation must invalidate the registered result",encoding="utf-8")
        with self.assertRaises(ValueError): quality.stage_evidence(self.state(),"review",{})

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_render_duration_mismatch_cannot_create_computed_quality_evidence(self):
        self.quality_fixture(mode="preview",collect=False)
        shorter = self.root / "shorter.mp4"
        subprocess.run(["ffmpeg","-v","error","-f","lavfi","-i","testsrc2=size=64x64:rate=30:duration=1", "-an","-c:v","libx264",str(shorter)],check=True,capture_output=True)
        self.call("quality-evidence","--video",shorter,"--out",self.root/"wrong-duration",expected=1)
        self.assertNotIn("evidence",self.state()["quality"])
        self.assertFalse((self.root/"wrong-duration").exists())

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_quality_collect_preserves_more_than_150_required_frames(self):
        self.quality_fixture(mode="preview",collect=False)
        timeline = guard.load(self.timeline_path)
        timeline["fps"] = 60
        timeline["shots"][0].update(output_in=0,output_out=3)
        timeline["shots"][1].update(output_in=3,output_out=6)
        guard.save(self.timeline_path,timeline)
        cues = self.root / "many-visual-cues.json"
        guard.save(cues,{"timing_source":"provisional","cues":[{"start":2*i/60,"end":(2*i+2)/60} for i in range(160)]})
        plan = guard.load(self.plan_path); plan["timing"] = str(cues)
        plan["sections"][1]["settled_at"] = 3.2
        guard.save(self.plan_path,plan)
        self.call("quality-plan","--plan",self.plan_path,"--creator-id","synthetic-creator")
        subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i","testsrc2=size=64x64:rate=60:duration=6","-an","-c:v","libx264",str(self.video)],check=True,capture_output=True)
        expected_frames = quality.expected_frames(plan,60,360)
        self.assertGreater(len(expected_frames),150)
        self.call("quality-evidence","--video",self.video,"--out",self.root/"many-frame-evidence")
        package = quality.evidence(self.state())
        self.assertEqual([image["frame"] for image in package["images"]],expected_frames)
        # Independently decode every source frame without a select expression.
        # Compare actual PNG bytes at every required index, not only declared labels.
        reference = self.root/"all-decoded-frames"; reference.mkdir()
        subprocess.run(["ffmpeg","-v","error","-xerror","-i",str(self.video),"-fps_mode","passthrough",str(reference/"frame_%05d.png")],check=True,capture_output=True)
        self.assertEqual(len(list(reference.glob("frame_*.png"))),360)
        for image in package["images"]:
            self.assertEqual(quality.sha(image["path"]),quality.sha(reference/f"frame_{image['frame']+1:05d}.png"))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "media tools unavailable")
    def test_quality_collect_failure_reports_ffmpeg_stderr_tail(self):
        self.quality_fixture(mode="preview",collect=False)
        failure = subprocess.CalledProcessError(244,["ffmpeg"],stderr=b"synthetic ffmpeg error prefix\nError while parsing expression\nCannot allocate memory\n")
        actual_run = subprocess.run
        def fail_only_ffmpeg(command, *args, **kwargs):
            if command[0] == "ffmpeg": raise failure
            return actual_run(command, *args, **kwargs)
        with patch.object(quality.subprocess,"run",side_effect=fail_only_ffmpeg):
            result = self.call("quality-evidence","--video",self.video,"--out",self.root/"failed-extraction",expected=1)
        self.assertIn("244",result["error"])
        self.assertIn("Error while parsing expression",result["error"])
        self.assertIn("Cannot allocate memory",result["error"])
        self.assertNotIn("evidence",self.state()["quality"])
        self.assertFalse((self.root/"failed-extraction/package.json").exists())

    def test_explicit_user_still_label_override_binds_instruction_file(self):
        self.quality_fixture(library=False,collect=False)
        plan=guard.load(self.plan_path);evidence=self.root/'user-instruction.txt'
        evidence.write_text('用户明确要求删除本段静帧提示，正文和来源身份不变',encoding='utf-8')
        plan['sections'][0].update(still=True,still_label_override={'authority':'user','instruction':'用户明确要求删除本段静帧提示','evidence':str(evidence)})
        guard.save(self.plan_path,plan)
        self.call('quality-plan','--plan',self.plan_path,'--creator-id','synthetic-creator')
        self.assertIn(str(evidence.resolve()),self.state()['quality']['design']['snapshots'])
        evidence.write_text('指令发生变化',encoding='utf-8')
        with self.assertRaises(ValueError):quality.unchanged(self.state()['quality']['design']['snapshots'])

    def test_unlabeled_still_without_user_override_rejected(self):
        self.quality_fixture(library=False,collect=False)
        plan=guard.load(self.plan_path);plan['sections'][0]['still']=True;guard.save(self.plan_path,plan)
        self.call('quality-plan','--plan',self.plan_path,'--creator-id','synthetic-creator',expected=1)

    def test_self_approved_or_missing_evidence_still_override_rejected(self):
        self.quality_fixture(library=False,collect=False)
        plan=guard.load(self.plan_path)
        for override in [{'authority':'creator','instruction':'我自行决定删除辅助静帧提示','evidence':str(self.engine)},
                         {'authority':'user','instruction':'用户明确要求删除本段静帧提示','evidence':str(self.root/'missing')}]:
            plan['sections'][0].update(still=True,still_label_override=override);guard.save(self.plan_path,plan)
            self.call('quality-plan','--plan',self.plan_path,'--creator-id','synthetic-creator',expected=1)

    def test_bounded_voice_chunk_and_limit_files_are_exit_dependencies(self):
        state=self.state();state.update(route=['intake','voice_input'],mode='voice');guard.save(self.state_file,state)
        self.finish('intake')
        source=self.root/'approved-script.json';evidence=self.root/'user-limit.txt'
        guard.save(source,{'script_status':'final','narration_text':'完整文字。'*150})
        evidence.write_text('用户明确说明当前音色单次上限500字符，请拆开配音',encoding='utf-8')
        self.call('lock-script','--file',source,'--authority','delegated','--evidence',evidence)
        text,data=voice.prepare(guard.load(source),500,evidence,'user')
        full=self.root/'whole.txt';full.write_text(text,encoding='utf-8')
        for chunk in data['chunks']:
            path=self.root/('part-%s.txt'%chunk['index']);path.write_text(chunk['text'],encoding='utf-8');chunk['text_file']=str(path.resolve())
        data.update(source=str(source.resolve()),source_sha256=guard.file_hash(source),text_file=str(full.resolve()))
        manifest=self.root/'voice-input.json';guard.save(manifest,data)
        self.finish('voice_input',[{'path':str(manifest),'role':'voice_input'}])
        snapshots=self.state()['stages']['voice_input']['file_snapshots']
        self.assertIn(str(evidence.resolve()),snapshots)
        part=Path(data['chunks'][0]['text_file']);self.assertIn(str(part.resolve()),snapshots)
        part.write_text('修改后不能继续沿用已通过状态',encoding='utf-8')
        self.assertEqual(self.call('summary')['stages'][-1]['status'],'pending_or_stale')

    def test_asset_package_does_not_expand_to_video_or_narration(self):
        self.state_file.unlink(); self.call("init","--mode","asset_package","--voice","none","--subtitles","none")
        for stage in self.state()["route"]: self.finish(stage)
        self.assertNotIn("export",self.state()["route"])
        self.assertNotIn("jianying_voice",self.state()["route"])
        self.assertTrue(all(row["status"] == "verified" for row in self.call("summary")["stages"]))


class WholeTextTests(unittest.TestCase):
    def test_complete_paragraph_preserves_punctuation_and_words(self):
        text, manifest = voice.prepare({"script_status":"final","narration_text":"先输入完整内容。\n再一次朗读，不要拆开！"})
        self.assertEqual(text,"先输入完整内容。 再一次朗读，不要拆开！")
        self.assertEqual((manifest["text_object_count"],manifest["planned_generation_count"]),(1,1))

    def test_draft_and_subtitle_only_source_rejected(self):
        for document in [{"script_status":"draft","narration_text":"草稿不能直接配音"},
                         {"script_status":"final","cues":[{"text":"不能猜回标点"}]}]:
            with self.assertRaises(ValueError): voice.prepare(document)

    def test_srt_timecodes_rejected_as_voice_input(self):
        with self.assertRaises(ValueError):
            voice.prepare({"script_status":"final","narration_text":"1\n00:00:00,000 --> 00:00:03,000\n不要逐条朗读"})

    def test_sentence_tts_manifest_cannot_masquerade_as_whole_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"input.json"
            guard.save(path,{"mode":"sentence_srt","text_object_count":5,"planned_generation_count":5})
            with self.assertRaises(ValueError): guard.validate_artifact({"path":str(path),"role":"voice_input"},{})

    def test_boolean_counts_rejected_as_numeric_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"input.json"
            guard.save(path,{"mode":"whole_paragraph","text_object_count":True,"planned_generation_count":True})
            with self.assertRaises(ValueError): guard.validate_artifact({"path":str(path),"role":"voice_input"},{})


if __name__ == "__main__":
    unittest.main()
