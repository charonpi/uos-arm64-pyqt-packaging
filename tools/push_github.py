#!/usr/bin/env python3
"""Push the current git index to GitHub through the Git Data API.

Useful when `git push` over HTTPS is blocked (e.g. an integration token that can
call the REST API but has no git push permission). Binary files such as .zip and
.png are uploaded as base64 blobs, exactly like text files.

Requirements: GITHUB_TOKEN in the environment (or --token-source gcm for a
cached Git Credential Manager login), and a local git repo with committed files
(`git ls-files` decides what is uploaded).

An empty repository (zero commits) rejects POST /git/blobs with HTTP 409, so the
script seeds it through the Contents API first and then attaches the full tree
as a child commit -- no force-push needed.

Usage:
    python3 tools/push_github.py --owner charonpi --repo uos-arm64-pyqt-packaging
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com"


def request(method: str, path: str, token: str, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "uos-arm64-pyqt-packaging-release",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError("%s %s -> HTTP %s: %s" % (method, path, exc.code, detail)) from exc


def is_missing_ref(exc: RuntimeError) -> bool:
    """A zero-commit GitHub repo answers 409 "Git Repository is empty", not 404."""
    text = str(exc)
    return "HTTP 404" in text or ("HTTP 409" in text and "Git Repository is empty" in text)


def bootstrap_if_empty(repo_path: str, token: str, branch: str, rels: list[str]) -> None:
    """Seed a zero-commit repository so the Git Data API becomes usable."""
    try:
        request("GET", repo_path + "/git/ref/heads/" + branch, token)
        print("Repository already has a " + branch + " ref")
        return
    except RuntimeError as exc:
        if not is_missing_ref(exc):
            raise

    seed = "README.md" if "README.md" in rels else rels[0]
    payload = {
        "message": "chore: initialize repository",
        "content": base64.b64encode((ROOT / seed).read_bytes()).decode("ascii"),
    }
    request("PUT", repo_path + "/contents/" + seed, token, payload)
    print("Seeded empty repository with " + seed)


def head_sha(repo_path: str, token: str, branch: str):
    """Return the current commit sha on branch, or None if the ref is absent."""
    try:
        ref = request("GET", repo_path + "/git/ref/heads/" + branch, token)
        return ref["object"]["sha"]
    except RuntimeError as exc:
        if is_missing_ref(exc):
            return None
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", default="charonpi")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--message", default="feat: v1.0.0 UOS 20 arm64 PyQt packaging skill + CLI toolkit")
    ap.add_argument("--token-source", choices=("env", "gcm"), default="env",
                    help="env = $GITHUB_TOKEN; gcm = cached Git Credential Manager login")
    args = ap.parse_args()

    if args.token_source == "gcm":
        env = dict(os.environ, GCM_INTERACTIVE="never", GIT_TERMINAL_PROMPT="0")
        proc = subprocess.run(["git", "credential", "fill"], cwd=str(ROOT), env=env,
                              input="protocol=https\nhost=github.com\n\n",
                              capture_output=True, text=True)
        token = next((line.split("=", 1)[1] for line in proc.stdout.splitlines()
                      if line.startswith("password=")), None)
        if not token:
            print("ERROR: no cached GitHub credential in Git Credential Manager", file=sys.stderr)
            return 2
        print("Using cached Git Credential Manager login")
    else:
        token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN is not set", file=sys.stderr)
        return 2

    repo_path = "/repos/%s/%s" % (args.owner, args.repo)
    out = subprocess.check_output(["git", "ls-files", "-z"], cwd=str(ROOT))
    rels = [p for p in out.decode("utf-8").split("\0") if p]
    if not rels:
        print("ERROR: git index is empty", file=sys.stderr)
        return 2
    print("Uploading %d files..." % len(rels))
    bootstrap_if_empty(repo_path, token, args.branch, rels)
    parent = head_sha(repo_path, token, args.branch)

    tree = []
    for i, rel in enumerate(rels, 1):
        blob = (ROOT / rel).read_bytes()
        res = request("POST", repo_path + "/git/blobs", token,
                      {"content": base64.b64encode(blob).decode("ascii"), "encoding": "base64"})
        mode = "100755" if rel.endswith(".sh") else "100644"
        tree.append({"path": rel, "mode": mode, "type": "blob", "sha": res["sha"]})
        if i % 10 == 0 or i == len(rels):
            print("  blobs: %d/%d" % (i, len(rels)))

    tree_res = request("POST", repo_path + "/git/trees", token, {"tree": tree})
    commit_payload = {"message": args.message, "tree": tree_res["sha"]}
    if parent:
        commit_payload["parents"] = [parent]
    commit = request("POST", repo_path + "/git/commits", token, commit_payload)

    if parent:
        # GET a single ref uses /git/ref/<ref>, but PATCH uses /git/refs/<ref>.
        request("PATCH", repo_path + "/git/refs/heads/" + args.branch, token,
                {"sha": commit["sha"], "force": False})
        print("Updated existing branch " + args.branch)
    else:
        request("POST", repo_path + "/git/refs", token,
                {"ref": "refs/heads/" + args.branch, "sha": commit["sha"]})
        print("Created branch " + args.branch)

    try:
        request("PATCH", repo_path, token, {"default_branch": args.branch})
    except RuntimeError as exc:
        print("WARN: could not set default branch: %s" % exc)

    print("OK: commit %s" % commit["sha"])
    print("    https://github.com/%s/%s" % (args.owner, args.repo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
