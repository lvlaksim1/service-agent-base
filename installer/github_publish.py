"""GitHub fast-forward-only multi-file publication, guarded by expected branch HEAD."""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from urllib.parse import quote

from .durable_state import DurableStateError


def publish_files(files, changes, repository, branch, expected_head, *, message):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise DurableStateError("GITHUB_TOKEN is required for publication")
    if not isinstance(expected_head, str) or len(expected_head) != 40 or any(x not in "0123456789abcdef" for x in expected_head):
        raise DurableStateError("expected HEAD must be 40 lowercase hex characters")
    if not repository or repository.count("/") != 1 or not branch or ".." in branch:
        raise DurableStateError("invalid repository or branch")
    base = f"https://api.github.com/repos/{repository}"
    def request(method, suffix, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(base + suffix, data=data, method=method, headers={
            "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "service-agent-base-durable",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise DurableStateError(f"GitHub {method} {suffix} returned HTTP {exc.code}") from exc

    ref = "heads/" + quote(branch, safe="/")
    current = request("GET", "/git/ref/" + ref)["object"]["sha"]
    if current != expected_head:
        raise DurableStateError("branch moved before publication")
    parent = request("GET", "/git/commits/" + expected_head)
    tree = []
    for path, content in sorted(changes.items()):
        if path not in files and not path.startswith(".context/service-agent/") and path != ".context/current/working-index.json":
            raise DurableStateError(f"unexpected path in publication: {path}")
        # Verify preimage against the expected commit; never overwrite unexpected remote changes.
        if path in files:
            encoded = quote(path, safe="/")
            remote = request("GET", "/contents/" + encoded + "?ref=" + expected_head)
            old = base64.b64decode(remote["content"]).decode("utf-8")
            if old != files[path]:
                raise DurableStateError(f"local snapshot differs from remote HEAD: {path}")
        blob = request("POST", "/git/blobs", {"content": content, "encoding": "utf-8"})["sha"]
        tree.append({"path": path, "mode": "100644", "type": "blob", "sha": blob})
    new_tree = request("POST", "/git/trees", {"base_tree": parent["tree"]["sha"], "tree": tree})["sha"]
    commit = request("POST", "/git/commits", {"message": message, "tree": new_tree, "parents": [expected_head]})["sha"]
    # No force: if HEAD moved, a sibling commit is not fast-forward and GitHub rejects it.
    request("PATCH", "/git/refs/" + ref, {"sha": commit, "force": False})
    return commit
