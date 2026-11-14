#!/usr/bin/env python3
"""Rewrites the download section of README.md so each button points at the newest installer.

For each system it picks the newest finished release, or the newest development build when
no finished release exists yet. Run by the publish workflow after every release.
"""
import json
import os
import re
import subprocess

REPO = os.environ["GITHUB_REPOSITORY"]
START, END = "<!-- downloads:start -->", "<!-- downloads:end -->"
TARGETS = [
    ("windows-", "win-Setup.exe", "assets/download-windows.svg", "Download MockMason for Windows", "Windows"),
    ("macos-", "osx-x64-Setup.pkg", "assets/download-macos-intel.svg", "Download MockMason for Mac with Intel", "macOS Intel"),
    ("macos-", "osx-arm64-Setup.pkg", "assets/download-macos-apple-silicon.svg", "Download MockMason for Mac with Apple Silicon", "macOS Apple Silicon"),
]


def releases():
    raw = subprocess.check_output(["gh", "api", f"repos/{REPO}/releases?per_page=100"])
    return [r for r in json.loads(raw) if not r.get("draft")]


def installer(release, ending):
    """The installer file in a release. Its name carries the version, so match on the ending."""
    for asset in release.get("assets", []):
        if asset["name"].startswith("MockMason-") and asset["name"].endswith(ending):
            return asset["name"]
    return None


def newest(all_releases, prefix, ending):
    def has_asset(release):
        return installer(release, ending) is not None

    mine = [r for r in all_releases if r["tag_name"].startswith(prefix) and has_asset(r)]
    if not mine:  # Older releases carried every system under one tag.
        mine = [r for r in all_releases if r["tag_name"].startswith("v") and has_asset(r)]
    finished = [r for r in mine if not r.get("prerelease")]
    pool = finished or mine
    return max(pool, key=lambda r: r["created_at"]) if pool else None


def main():
    all_releases = releases()
    buttons, versions = [], []
    for prefix, ending, image, alt, label in TARGETS:
        release = newest(all_releases, prefix, ending)
        if release is None:
            url = f"https://github.com/{REPO}/releases"
            versions.append(f"{label}: not published yet")
        else:
            tag = release["tag_name"]
            asset = installer(release, ending)
            url = f"https://github.com/{REPO}/releases/download/{tag}/{asset}"
            version = re.sub(r"^(windows-|macos-)?v", "", tag)
            kind = " (development build)" if release.get("prerelease") else ""
            versions.append(f"{label}: {version}{kind}")
        buttons.append(f'  <a href="{url}"><img src="{image}" alt="{alt}" height="72"></a>')

    block = "\n".join(
        [START, '<p align="center">', *buttons, "</p>", "", "Current versions: " + " · ".join(versions) + ".", END]
    )
    with open("README.md", encoding="utf-8") as handle:
        text = handle.read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit("README.md is missing the download markers.")
    with open("README.md", "w", encoding="utf-8") as handle:
        handle.write(pattern.sub(lambda _: block, text))


if __name__ == "__main__":
    main()
