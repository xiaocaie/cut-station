# Publishing a public copy

Publish only the contents of this sanitized repository. Keep local backup snapshots, audit scratch directories, user media, project states and private test evidence outside it. Start a fresh Git history from this copy; do not publish an old history that ever contained private files. A later deletion from the working tree does not remove earlier commits.

## Before each release

Run from the repository root:

```bash
python3 scripts/release_check.py
python3 -m unittest discover -s tests -v
```

The checker verifies local references, sections, catalog shape, font hashes/notices and a limited set of secret/private-path patterns. It reports locations without printing matched secrets. It does not establish permission to distribute arbitrary new documents/media. Inspect new asset content, image metadata, rights and full Git history independently; a narrow pattern scan is not proof of complete anonymization.

Use a clean GitHub repository or upload this directory's contents. SKILL.md belongs at the root. Include README, scripts, references, assets, tests, workflow-manifest.json, recommended-skills.json, license/notices and CI. Do not upload the surrounding outputs folder, personal audit report or original installed skill. A ZIP is convenient for download/release assets; extract its contents when populating the repository.

Keep project outputs/logs/credentials out of Git using .gitignore, but do not treat .gitignore as a privacy filter: it does not clean tracked files, old history, manual web uploads or release attachments. Review the actual staged file list and selected upload folder. Do not run an unreviewed `git add .` in the parent workspace.

## Licensing and claims

MIT applies to this package's original public instructions/helpers. Bundled fonts retain OFL. Four recommended upstream projects are not vendored or relicensed; they are independently downloaded after consent. External renderer, sound, image and service terms remain applicable. Verify redistribution rights before adding any new asset. No company/client intellectual property is licensed by this file.

Describe capabilities honestly: standard-format support and helper tests are distinct from a full real-agent film test. Do not claim universal compatibility, identical quality, unconditional free rendering or unlimited free narration. Pin and record dependency source revisions; reassess versions and licensing when updating them.

For a first public release, use a pre-release version while real cross-agent full-film testing remains incomplete. Include actual validation boundaries in release notes. A public filename or branding search does not establish trademark clearance or an exclusive name.

For offline checks the package folder must be named `cut-station`, matching SKILL.md. GitHub automatic source ZIPs may append a branch name; rename the extracted folder or run checks on the installed skill folder.
