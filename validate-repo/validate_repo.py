"""Check that a mod repo has the files and metadata the org expects.

Usage:
    python validate_repo.py [<repo dir>]

The repo dir defaults to the current directory. Prints GitHub annotations for every problem found and exits 1 if there was any.
"""

import hashlib
import sys
from pathlib import Path

import yaml

LICENSE_TEMPLATE = Path(__file__).resolve().parent / "LICENSE.template"

# page: is the section the org page reads; these keys must be filled in.
PAGE_REQUIRED = ["title", "game", "summary"]
PAGE_PATHS = ["description_path", "preview_path"]

WORKSHOP_REQUIRED = ["app_id", "publishedfield_id", "visibility"]
# Steam visibility: 0 public, 1 friends-only, 2 private, 3 unlisted
WORKSHOP_VISIBILITY = {0, 1, 2, 3}

errors = []


def error(message, file=None):
    errors.append(message)
    location = f" file={file}" if file else ""
    print(f"::error{location}::{message}")


def license_hash(path):
    # Compare with LF endings so a CRLF checkout does not count as different.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def check_license(repo):
    path = repo / "LICENSE"
    if not path.is_file():
        error("Missing LICENSE")
        return
    expected, actual = license_hash(LICENSE_TEMPLATE), license_hash(path)
    if actual != expected:
        error(f"LICENSE differs from the org template (sha256 {actual[:12]}, expected {expected[:12]})", "LICENSE")


def check_path(repo, section, key, value):
    if not isinstance(value, str) or not (repo / value).is_file():
        error(f"{section}.{key} points to a missing file: {value}", "metadata.yml")


def check_page(repo, page):
    if not isinstance(page, dict):
        error("metadata.yml has no page: section", "metadata.yml")
        return
    for key in PAGE_REQUIRED:
        value = page.get(key)
        if not isinstance(value, str) or not value.strip():
            error(f"page.{key} is required", "metadata.yml")
    for key in PAGE_PATHS:
        if key in page:
            check_path(repo, "page", key, page[key])
    if "hidden" in page and not isinstance(page["hidden"], bool):
        error("page.hidden must be true or false", "metadata.yml")


def check_github(github):
    if github is None:
        return
    if not isinstance(github, dict):
        error("github: must be a mapping", "metadata.yml")
        return
    if not github.get("description"):
        error("github.description is required", "metadata.yml")
    if "mod" not in (github.get("topics") or []):
        error("github.topics must include 'mod'", "metadata.yml")


def check_workshop(repo, workshop):
    if workshop is None:
        return
    if not isinstance(workshop, dict):
        error("workshop: must be a mapping", "metadata.yml")
        return
    for key in WORKSHOP_REQUIRED:
        if key not in workshop:
            error(f"workshop.{key} is required", "metadata.yml")
    if "visibility" in workshop and workshop["visibility"] not in WORKSHOP_VISIBILITY:
        error(f"workshop.visibility must be one of 0-3, got {workshop['visibility']!r}", "metadata.yml")
    if "preview_path" in workshop:
        check_path(repo, "workshop", "preview_path", workshop["preview_path"])
    for lang, loc in (workshop.get("localizations") or {}).items():
        if isinstance(loc, dict) and "description_path" in loc:
            check_path(repo, f"workshop.localizations.{lang}", "description_path", loc["description_path"])


def check_metadata(repo):
    path = repo / "metadata.yml"
    if not path.is_file():
        error("Missing metadata.yml")
        return
    try:
        meta = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        error(f"metadata.yml is not valid YAML: {exc}", "metadata.yml")
        return
    if not isinstance(meta, dict):
        error("metadata.yml must be a mapping", "metadata.yml")
        return
    check_page(repo, meta.get("page"))
    check_github(meta.get("github"))
    check_workshop(repo, meta.get("workshop"))


def main():
    if len(sys.argv) > 2:
        sys.exit(__doc__)
    repo = Path(sys.argv[1] if len(sys.argv) == 2 else ".")
    check_license(repo)
    check_metadata(repo)
    if errors:
        print(f"{len(errors)} problem(s) found.")
        sys.exit(1)
    print("Repo is valid.")


if __name__ == "__main__":
    main()
