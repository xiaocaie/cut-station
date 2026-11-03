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
        guard.save(report, {"stage":stage,"checks":[{"id":key,"status":"verified", "note":"本项使用合成测试证据验证文件及阶段状态的门禁逻辑", "evidence":[str(evidence)]}
                                                    for key in self.manifest["stages"][stage]["checks"]],
                            "artifacts":artifacts or []})
        self.call("exit", "--stage", stage, "--report", report)

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

    def test_legal_font_route_finishes_with_sources_unchanged(self):
        audio = self.root / "original-audio.bin"
        audio.write_bytes(b"preserved-voice")
        self.call("protect","--file",audio)
        for stage in self.state()["route"]:
            self.finish(stage)
        self.assertTrue(all(x["status"] == "verified" for x in self.call("summary")["stages"]))
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
