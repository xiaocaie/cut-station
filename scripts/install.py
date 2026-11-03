#!/usr/bin/env python3
"""Install this skill and optionally download four recommended skill projects.

No package-manager hooks, account setup, renderer installation or app automation.
Existing destinations are preserved. Python 3.9+ and git (for recommendations).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = shutil.ignore_patterns(".git", ".DS_Store", "__pycache__", "*.pyc", "node_modules")


def default_destination(agent):
    if agent == "codex":
        return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills"
    return Path.home() / (".claude" if agent == "claude-code" else ".agents") / "skills"


def same_files(source, target):
    def hashes(root):
        result = {}
        for path in root.rglob("*"):
            if path.is_file() and not any(p in (".git", "__pycache__", "node_modules", ".DS_Store") for p in path.relative_to(root).parts) and path.suffix != ".pyc":
                result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return result
    return target.is_dir() and hashes(source) == hashes(target)


def install_tree(source, target):
    if target.exists() or target.is_symlink():
        return "already_current" if source.resolve() == target.resolve() or same_files(source, target) else "preserved_existing"
    for path in source.rglob("*"):
        if path.is_symlink() and not path.resolve().is_relative_to(source.resolve()):
            raise ValueError("Source symlink points outside the selected skill: " + str(path.relative_to(source)))
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".cut-station-install-", dir=str(target.parent)) as temporary:
        staged = Path(temporary) / "skill"
        shutil.copytree(source, staged, ignore=EXCLUDED)
        # Never overwrite a destination created since the initial check.
        if target.exists() or target.is_symlink():
            return "preserved_existing"
        staged.rename(target)
    return "installed"


def choose_recommendations(value, catalog, interactive=None):
    keys = list(catalog)
    if value == "ask":
        for key, entry in catalog.items():
            companions = ", ".join(s["name"] for s in entry["skills"][1:])
            suffix = " (companions: " + companions + ")" if companions else ""
            print("  " + key + ": " + entry["repository"] + " @ " + entry["ref"][:12] + suffix)
        print("Recommended skill files only; tools, accounts and paid services are not configured.")
        if interactive is None:
            interactive = sys.stdin.isatty()
        if not interactive:
            print("No interactive input: recommendations remain pending. Pass --recommended all, none, or comma-separated keys.")
            return [], "pending_user_choice"
        value = input("Install recommendations? [all / none / comma-separated keys; default none]: ").strip() or "none"
    if value == "none":
        return [], "declined"
    if value == "all":
        return keys, "explicit_all"
    selected = list(dict.fromkeys(part.strip() for part in value.split(",") if part.strip()))
    if not selected or any(key not in catalog for key in selected):
        raise ValueError("Choose all, none, or these keys: " + ", ".join(keys))
    return selected, "explicit_selection"


def fetch_source(entry, destination):
    if not shutil.which("git"):
        raise ValueError("git is required only for downloading recommendations")
    repository, ref = entry["repository"], entry["ref"]
    import re
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not re.fullmatch(r"[0-9a-f]{40}", ref):
        raise ValueError("Invalid repository or immutable ref")
    def run(argv):
        result = subprocess.run(argv, capture_output=True, text=True, timeout=180)
        if result.returncode:
            raise ValueError("git download failed: " + result.stderr[-1200:])
        return result.stdout.strip()
    run(["git", "init", "--quiet", str(destination)])
    empty_hooks = destination / ".git" / "cut-station-empty-hooks"
    empty_hooks.mkdir()
    run(["git", "-C", str(destination), "remote", "add", "origin", "https://github.com/" + repository + ".git"])
    run(["git", "-C", str(destination), "config", "remote.origin.promisor", "true"])
    run(["git", "-C", str(destination), "config", "remote.origin.partialclonefilter", "blob:none"])
    paths = list(dict.fromkeys(skill["path"] for skill in entry["skills"]))
    if "." not in paths:
        run(["git", "-C", str(destination), "sparse-checkout", "init", "--cone"])
        run(["git", "-C", str(destination), "sparse-checkout", "set", "--cone", "--", *paths])
    run(["git", "-C", str(destination), "-c", "core.hooksPath=" + str(empty_hooks), "fetch", "--quiet", "--filter=blob:none", "--no-tags", "--depth=1", "origin", ref])
    run(["git", "-C", str(destination), "-c", "core.hooksPath=" + str(empty_hooks), "checkout", "--quiet", "--detach", "FETCH_HEAD"])
    if run(["git", "-C", str(destination), "rev-parse", "HEAD"]) != ref:
        raise ValueError("Downloaded commit does not match the declared ref")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=["codex", "claude-code", "generic"], default="generic")
    parser.add_argument("--dest", type=Path, help="Explicit skills root; useful for other hosts and project-local installs")
    parser.add_argument("--recommended", default="ask", help="ask (default), all, none, or comma-separated catalog keys")
    parser.add_argument("--reconfigure", action="store_true", help="Ask again instead of reusing a recorded choice")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true", help="Read the local setup receipt without installing or prompting")
    args = parser.parse_args(argv)
    try:
        catalog = json.loads((ROOT / "recommended-skills.json").read_text(encoding="utf-8"))["projects"]
        destination = (args.dest or default_destination(args.agent)).expanduser().resolve()
        if args.dry_run:
            print(json.dumps({"destination":str(destination),"base_skill":"cut-station", "recommendations":catalog,
                              "writes":False,"downloads":False}, ensure_ascii=False, indent=2))
            return 0
        receipt_path = destination / ".cut-station-setup.json"
        if receipt_path.is_symlink():
            raise ValueError("Setup receipt must be a regular local file, not a symlink")
        catalog_hash = hashlib.sha256(json.dumps(catalog,sort_keys=True).encode()).hexdigest()
        previous = {}
        if receipt_path.is_file():
            try:
                previous = json.loads(receipt_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                previous = {}
        if args.status:
            print(json.dumps({"receipt":previous,"catalog_matches":isinstance(previous,dict) and previous.get("catalog_sha256") == catalog_hash,
                              "path":str(receipt_path),"writes":False,"downloads":False},ensure_ascii=False,indent=2))
            return 0
        if (args.recommended == "ask" and not args.reconfigure and isinstance(previous,dict)
                and previous.get("catalog_sha256") == catalog_hash
                and previous.get("choice") != "pending_user_choice"
                and isinstance(previous.get("selected"),list)
                and all(isinstance(key,str) and key in catalog for key in previous["selected"])):
            selected, choice = previous["selected"], "reused_previous_choice"
            print("Reusing recorded recommendation choice; pass --reconfigure to change it.")
        else:
            selected, choice = choose_recommendations(args.recommended, catalog)
        target = destination / "cut-station"
        if destination == ROOT or ROOT in destination.parents:
            raise ValueError("Installation destination must be outside the source package")
        result = {"base":install_tree(ROOT, target), "path":str(target), "choice":choice, "recommended":[]}
        failures = []
        for key in selected:
            entry = catalog[key]
            absent = [s for s in entry["skills"] if not (destination / s["name"]).exists() and not (destination / s["name"]).is_symlink()]
            for skill in entry["skills"]:
                if skill not in absent:
                    result["recommended"].append({"key":key,"name":skill["name"],"status":"preserved_existing"})
            if not absent:
                continue
            try:
                with tempfile.TemporaryDirectory(prefix="cut-station-source-") as temporary:
                    checkout = Path(temporary) / "repo"
                    print("Fetching " + key + " from " + entry["repository"] + " @ " + entry["ref"][:12], flush=True)
                    fetch_source(entry, checkout)
                    for skill in absent:
                        source = (checkout / skill["path"]).resolve()
                        if not source.is_relative_to(checkout.resolve()) or not (source / "SKILL.md").is_file():
                            raise ValueError("Expected skill entry missing: " + skill["path"])
                        status = install_tree(source, destination / skill["name"])
                        result["recommended"].append({"key":key,"name":skill["name"],"status":status,"ref":entry["ref"]})
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                failures.append({"key":key,"error":str(exc)})
        result["failures"] = failures
        result["runtime_ready"] = False
        receipt = {"schema_version":1,"catalog_sha256":catalog_hash,"choice":choice,
                   "selected":selected,"recommended":result["recommended"],"failures":failures}
        with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=str(destination),prefix=".cut-station-receipt-",delete=False) as handle:
            handle.write(json.dumps(receipt,ensure_ascii=False,indent=2) + "\n")
            staged_receipt = Path(handle.name)
        staged_receipt.replace(receipt_path)
        result["setup_receipt"] = str(receipt_path)
        result["next"] = "Reload/rescan skills in the host; run route-specific preflight and a real sample. No tools or paid services were installed."
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if failures else 0
    except (OSError, ValueError, EOFError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
