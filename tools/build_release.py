"""Builds the release package from main (maintainers only).

    git checkout main && git pull && python tools/build_release.py

Creates dist/<name>.tar.gz, dist/<name>.tar.gz.sha256 and dist/notes.md (the CHANGELOG section of
the current VERSION), then prints the `gh release create` command to publish them.
The archive comes from `git archive`, so uncommitted changes are never released; files marked
`export-ignore` in .gitattributes (dev/, tools/, ...) are left out.
"""
import hashlib
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
NAME = (ROOT / "NAME").read_text().strip()
VERSION = (ROOT / "VERSION").read_text().strip()
DIST = ROOT / "dist"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


if git("status", "--porcelain").strip():
    sys.exit("Commit (or stash) your changes first: the release is built from HEAD.")
if git("rev-parse", "--abbrev-ref", "HEAD").strip() != "main":
    sys.exit("Releases are built from main: merge develop into main with a pull request, then "
             "`git checkout main && git pull`.")
git("fetch", "--quiet", "--tags", "origin", "main")
if git("rev-parse", "HEAD").strip() != git("rev-parse", "origin/main").strip():
    sys.exit("Your main is not the same as origin/main: run `git pull` (and push nothing to main directly).")
if git("tag", "-l", f"v{VERSION}").strip():
    sys.exit(f"v{VERSION} is already released: bump VERSION (and CHANGELOG.md) on develop.")
if not re.fullmatch(r"\d+\.\d+\.\d+", VERSION):
    sys.exit(f"VERSION must look like 1.2.3, found {VERSION!r}")

changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
m = re.search(rf"^## \[?v?{re.escape(VERSION)}\]?.*?$(.*?)(?=^## |\Z)", changelog, re.S | re.M)
if not m or not m.group(1).strip():
    sys.exit(f"Add a '## {VERSION}' section to CHANGELOG.md first.")

DIST.mkdir(exist_ok=True)
tar = DIST / f"{NAME}.tar.gz"
git("archive", "--format=tar.gz", f"--prefix={NAME}/", "-o", str(tar), "HEAD")
digest = hashlib.sha256(tar.read_bytes()).hexdigest()
# write_bytes: LF line endings on Windows too (sha256sum -c fails on "name\r")
(DIST / f"{NAME}.tar.gz.sha256").write_bytes(f"{digest}  {NAME}.tar.gz\n".encode())
(DIST / "notes.md").write_bytes((m.group(1).strip() + "\n").encode("utf-8"))

print(f"{tar.name}  {tar.stat().st_size} bytes  sha256 {digest}")
print("\nPublish with:")
print(f'  git tag v{VERSION} && git push origin v{VERSION}')
print(f'  gh release create v{VERSION} dist/{NAME}.tar.gz dist/{NAME}.tar.gz.sha256 '
      f'--title "v{VERSION}" --notes-file dist/notes.md')
