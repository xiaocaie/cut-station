#!/usr/bin/env python3
"""Offline package checks, with redacted findings. Not a complete privacy/rights audit."""
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".txt", ".csv", ".srt", ".svg"}


def inspect(root=ROOT):
    root = Path(root).resolve()
    errors, warnings = [], []
    patterns = {
        "personal_home_path": re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+/|[A-Za-z]:\\(?:Users)\\[A-Za-z0-9_.-]+\\"),
        "private_document_link": re.compile(r"https?://[^\s/)]+\.(?:feishu\.cn|larksuite\.com)/(?:docx|wiki|base|sheets)/[A-Za-z0-9]{8,}"),
        "private_chat_link": re.compile(r"https?://(?:chatgpt\.com|chat\.openai\.com)/(?:s|c)/[A-Za-z0-9_-]{8,}|codex://(?:threads|chat)/"),
        "credential_signature": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{25,}|sk-(?:proj-)?[A-Za-z0-9_-]{28,}|AKIA[A-Z0-9]{16})\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    }
    required = ["SKILL.md", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "recommended-skills.json", "workflow-manifest.json"]
    for name in required:
        if not (root / name).is_file():
            errors.append({"file":name,"check":"required_file_missing"})
    ignored = {".git", "__pycache__", "node_modules", ".venv", "venv"}
    files = [p for p in root.rglob("*") if p.is_file() and not any(part in ignored for part in p.relative_to(root).parts)]
    for path in files:
        rel = str(path.relative_to(root))
        if path.is_symlink():
            errors.append({"file":rel,"check":"symlink_not_permitted_in_release"})
        if path.name in (".DS_Store", ".env", ".cut-station-setup.json") or path.name.startswith(".env.") or path.suffix == ".pyc":
            errors.append({"file":rel,"check":"private_or_generated_file"})
        if path.stat().st_size > 25 * 1024 * 1024:
            warnings.append({"file":rel,"check":"exceeds_browser_upload_limit"})
        if path.suffix not in TEXT_SUFFIXES and path.name not in ("LICENSE", ".gitignore", ".gitattributes"):
            if path.suffix not in (".ttf", ".woff2"):
                errors.append({"file":rel,"check":"unreviewed_binary_type"})
            continue
        content = path.read_text(encoding="utf-8-sig")
        for label, pattern in patterns.items():
            for match in pattern.finditer(content):
                errors.append({"file":rel,"line":content[:match.start()].count("\n") + 1,"check":label})
        if path.suffix == ".json":
            try: json.loads(content)
            except ValueError: errors.append({"file":rel,"check":"invalid_json"})
        if path.suffix == ".md":
            # Only inline links/images, not code literals. No network lookups.
            outside_code = re.sub(r"```.*?```", "", content, flags=re.S)
            for match in re.finditer(r"!?\[[^\]]*\]\(([^\s)]+)\)", outside_code):
                link = unquote(match[1].split("#", 1)[0]).strip("<>")
                if not link or re.match(r"[a-z][a-z0-9+.-]*:", link): continue
                target = (path.parent / link).resolve()
                if not target.is_relative_to(root) or not target.exists():
                    errors.append({"file":rel,"check":"missing_or_external_local_reference","target":link})
    entry = root / "SKILL.md"
    if entry.exists():
        content = entry.read_text(encoding="utf-8")
        front = content.split("---", 2)
        if len(front) != 3:
            errors.append({"file":"SKILL.md","check":"missing_frontmatter"})
        else:
            name = re.search(r"^name:\s*(\S+)",front[1],re.M)
            if not name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",name[1]) or len(name[1]) > 64 or name[1] != root.name:
                errors.append({"file":"SKILL.md","check":"name_must_match_directory"})
            description = re.search(r"^description:\s*(.+)",front[1],re.M)
            if not description or len(description[1]) > 1024:
                errors.append({"file":"SKILL.md","check":"invalid_description"})
    manifest_path = root / "workflow-manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            specs = list(manifest["core_docs"])
            for stage in manifest["stages"].values(): specs.extend(stage["docs"])
            for feature in manifest["features"].values(): specs.extend(feature["docs"])
            for spec in specs:
                item = {"path":spec} if isinstance(spec,str) else spec
                if item["path"].startswith("@"):
                    if item["path"][1:] not in manifest["external_skills"]:
                        errors.append({"file":"workflow-manifest.json","check":"unknown_external_skill"})
                    continue
                path = (root / item["path"]).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    errors.append({"file":"workflow-manifest.json","check":"missing_packet","target":item["path"]})
                    continue
                if item.get("sections"):
                    headings = set(re.findall(r"^#{1,6}\s+(.+?)\s*$",path.read_text(encoding="utf-8"),re.M))
                    if not set(item["sections"]).issubset(headings):
                        errors.append({"file":item["path"],"check":"missing_required_section"})
        except (ValueError,KeyError,TypeError): errors.append({"file":"workflow-manifest.json","check":"invalid_manifest"})
    try:
        catalog = json.loads((root / "recommended-skills.json").read_text(encoding="utf-8"))["projects"]
        if set(catalog) != {"hyperframes","video-use","remotion","shotcraft"}: raise ValueError()
        for entry in catalog.values():
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",entry["repository"]) or not re.fullmatch(r"[a-f0-9]{40}",entry["ref"]): raise ValueError()
            for skill in entry["skills"]:
                if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",skill["name"]) or Path(skill["path"]).is_absolute() or ".." in Path(skill["path"]).parts: raise ValueError()
    except (OSError,ValueError,KeyError,TypeError): errors.append({"file":"recommended-skills.json","check":"invalid_pinned_catalog"})
    font_hashes = 0
    try:
        fonts = json.loads((root / "assets/fonts/manifest.json").read_text(encoding="utf-8"))["fonts"]
        for font in fonts:
            for key, hash_key in (("file","file_sha256"),("web_file","web_file_sha256"),("license_file","license_file_sha256")):
                if key not in font: continue
                path = root / "assets/fonts" / font[key]
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != font[hash_key]:
                    errors.append({"file":str(path.relative_to(root)),"check":"font_or_license_hash_mismatch"})
                font_hashes += 1
    except (OSError,ValueError,KeyError,TypeError): errors.append({"file":"assets/fonts/manifest.json","check":"invalid_font_manifest"})
    return {"passed":not errors,"file_count":len(files),"bytes":sum(p.stat().st_size for p in files),
            "font_hashes_checked":font_hashes,"errors":errors,"warnings":warnings,
            "excluded_directories":sorted(ignored),
            "not_proven":["all private information removed", "rights ownership of arbitrary added files", "clean remote Git history", "actual engine/host-agent/full-film success"]}


if __name__ == "__main__":
    result = inspect()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result["passed"] else 1)
