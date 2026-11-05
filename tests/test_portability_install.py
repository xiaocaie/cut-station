"""Observable installation/routing checks; no real desktop or paid API calls."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / "scripts"))
import install
import skill_paths
import workflow_guard as guard


class InstallationTests(unittest.TestCase):
    def test_skip_never_downloads(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(install,"fetch_source") as fetch, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(install.main(["--dest",temporary,"--recommended","none"]),0)
            self.assertTrue((Path(temporary)/"cut-station/SKILL.md").is_file())
            fetch.assert_not_called()

    def test_noninteractive_is_pending_not_consent(self):
        catalog={"remotion":{"repository":"owner/repo","ref":"a"*40,"skills":[{"name":"example","path":"."}]}}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(install.choose_recommendations("ask",catalog,interactive=False),([],"pending_user_choice"))

    def test_recorded_skip_is_reused_without_prompt_or_network(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(install,"fetch_source") as fetch, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(install.main(["--dest",temporary,"--recommended","none"]),0)
            with patch.object(install,"choose_recommendations",side_effect=AssertionError("must reuse prior choice")):
                self.assertEqual(install.main(["--dest",temporary]),0)
            receipt=json.loads((Path(temporary)/".cut-station-setup.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["selected"],[])
            self.assertEqual(receipt["choice"],"reused_previous_choice")
            fetch.assert_not_called()

    def test_reconfigure_does_not_reuse_recorded_choice(self):
        with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(install.main(["--dest",temporary,"--recommended","none"]),0)
            with patch.object(install,"choose_recommendations",return_value=([],"declined")) as choose:
                self.assertEqual(install.main(["--dest",temporary,"--reconfigure"]),0)
                choose.assert_called_once()

    def test_interactive_selection_and_decline(self):
        catalog={key:{"repository":"owner/repo","ref":"a"*40,"skills":[{"name":key,"path":"."}]} for key in ["remotion","shotcraft"]}
        with contextlib.redirect_stdout(io.StringIO()),patch("builtins.input",return_value="shotcraft"):
            self.assertEqual(install.choose_recommendations("ask",catalog,True)[0],["shotcraft"])
        with contextlib.redirect_stdout(io.StringIO()),patch("builtins.input",return_value=""):
            self.assertEqual(install.choose_recommendations("ask",catalog,True),([],"declined"))

    def test_existing_user_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); source=root/"source"; target=root/"target"
            source.mkdir(); target.mkdir()
            (source/"SKILL.md").write_text("new",encoding="utf-8"); (target/"SKILL.md").write_text("protected",encoding="utf-8")
            self.assertEqual(install.install_tree(source,target),"preserved_existing")
            self.assertEqual((target/"SKILL.md").read_text(),"protected")

    def test_selected_recommendation_only_and_rerun_preserves_it(self):
        def fixture_fetch(entry,destination):
            path=destination/entry["skills"][0]["path"]
            path.mkdir(parents=True); (path/"SKILL.md").write_text("synthetic upstream fixture",encoding="utf-8")
        with tempfile.TemporaryDirectory() as temporary, patch.object(install,"fetch_source",side_effect=fixture_fetch) as fetch, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(install.main(["--dest",temporary,"--recommended","remotion"]),0)
            self.assertEqual(fetch.call_count,1)
            self.assertTrue((Path(temporary)/"remotion-best-practices/SKILL.md").is_file())
            self.assertFalse((Path(temporary)/"hyperframes").exists())
            self.assertEqual(install.main(["--dest",temporary,"--recommended","remotion"]),0)
            self.assertEqual(fetch.call_count,1)

    def test_dry_run_has_no_files_or_network(self):
        with tempfile.TemporaryDirectory() as temporary,patch.object(install,"fetch_source") as fetch,contextlib.redirect_stdout(io.StringIO()):
            target=Path(temporary)/"uncreated"
            self.assertEqual(install.main(["--dest",str(target),"--dry-run"]),0)
            self.assertFalse(target.exists()); fetch.assert_not_called()


class PortableRoutesTests(unittest.TestCase):
    def test_no_narration_no_captions_has_no_voice_or_caption_stages(self):
        with tempfile.TemporaryDirectory() as temporary,contextlib.redirect_stdout(io.StringIO()):
            state=Path(temporary)/"workflow.json"
            with patch.object(sys,"argv",["guard","--state",str(state),"init","--mode","full","--voice","none","--subtitles","none"]):
                self.assertEqual(guard.main(),0)
            document=guard.load(state)
            for stage in ["voice_input","jianying_voice","audio_timing","srt"]:
                self.assertNotIn(stage,document["route"])
            self.assertIn("rough_edit",document["route"])
            self.assertIn("export",document["route"])

    def test_base_motion_packets_do_not_need_recommended_skills(self):
        manifest=guard.load(guard.MANIFEST)
        state={"route":["motion_sound_plan"],"features":[],"extra_docs":{}}
        with patch.object(guard,"resolve_skill",side_effect=AssertionError("base route must not resolve optional skills")):
            self.assertTrue(guard.packets(state,"motion_sound_plan",manifest))

    def test_foreign_host_root_and_explicit_mapping(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); entry=root/".claude/skills/remotion-best-practices/SKILL.md"
            entry.parent.mkdir(parents=True);entry.write_text("synthetic skill",encoding="utf-8")
            # Model an actual foreign installation; the current host's sibling
            # skills must not contaminate this discovery fixture.
            with patch.dict(os.environ,{"CUT_STATION_SKILL_PATHS":""}), patch.object(skill_paths,"__file__",str(root/".claude/skills/cut-station/scripts/skill_paths.py")):
                self.assertEqual(skill_paths.resolve_skill("remotion",home=root),entry.resolve())
                self.assertEqual(skill_paths.resolve_skill("remotion",override=entry.parent),entry.resolve())
                with self.assertRaises(ValueError): skill_paths.resolve_skill("remotion",override=root/"missing")

    def test_selected_engine_fails_with_actionable_missing_entry(self):
        manifest=guard.load(guard.MANIFEST)
        state={"route":["rough_edit"],"features":["engine_remotion"],"extra_docs":{}}
        with patch.object(guard,"resolve_skill",side_effect=ValueError("Optional skill missing: @remotion")):
            with self.assertRaisesRegex(ValueError,"@remotion"): guard.packets(state,"rough_edit",manifest)


if __name__ == "__main__": unittest.main()
