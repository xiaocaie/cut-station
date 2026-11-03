"""Resolve optional skill entrypoints across agent hosts without installing anything."""
import glob
import os
from pathlib import Path


ALIASES = {
    "hyperframes": ["hyperframes"],
    "hyperframes-cli": ["hyperframes-cli"],
    "video-use": ["video-use"],
    "remotion": ["remotion-best-practices"],
    "shotcraft": ["video-shotcraft"],
}


def skill_roots(project=None, home=None):
    home = Path(home) if home is not None else Path.home()
    roots = [Path(p).expanduser() for p in os.environ.get("CUT_STATION_SKILL_PATHS", "").split(os.pathsep) if p]
    roots.append(Path(__file__).resolve().parents[2])
    if project:
        project = Path(project).resolve()
        for base in (project, *project.parents):
            for agent in (".agents", ".claude", ".codex", ".cursor"):
                roots.append(base / agent / "skills")
    roots.extend(home / agent / "skills" for agent in (".agents", ".claude", ".codex", ".cursor"))
    roots.append(home / ".config/opencode/skills")
    return list(dict.fromkeys(roots))


def resolve_skill(key, project=None, override=None, legacy=None, home=None):
    """An explicit mapping must work; auto-discovery never silently replaces it."""
    if override:
        path = Path(override).expanduser()
        if path.is_dir():
            path /= "SKILL.md"
        if not path.is_file():
            raise ValueError("Explicit skill path does not exist: " + str(path))
        return path.resolve()
    for root in skill_roots(project, home):
        for name in ALIASES.get(key, [key]):
            path = root / name / "SKILL.md"
            if path.is_file():
                return path.resolve()
    # Existing Codex plugin installations remain usable; no version is pinned here.
    if key in ("hyperframes", "hyperframes-cli"):
        base = Path(home) if home is not None else Path.home()
        pattern = base / ".codex/plugins/cache/openai-curated-remote/hyperframes/*/skills" / key / "SKILL.md"
        matches = sorted(glob.glob(str(pattern)), key=lambda p: Path(p).stat().st_mtime)
        if matches:
            return Path(matches[-1]).resolve()
    if legacy:
        matches = sorted(glob.glob(str(Path(legacy).expanduser())), key=lambda p: Path(p).stat().st_mtime)
        if matches:
            return Path(matches[-1]).resolve()
    raise ValueError("Optional skill missing: @" + key + "; install it with consent, map --skill-path, or choose a route that does not require it")
