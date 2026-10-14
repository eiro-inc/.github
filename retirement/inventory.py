#!/usr/bin/env python3
"""Read-only retirement inventory; errors remain explicit, never imply absence.

Run with an authenticated gh CLI: python3 retirement/inventory.py > inventory.json
The output is evidence of configuration at capture time, not approval to remove it.
"""
import concurrent.futures
import datetime
import json
import subprocess


def gh(*args):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout)


def capture(repo):
    name = repo["name"]
    prefix = f"repos/eiro-inc/{name}"
    result = {"repository": f"eiro-inc/{name}", "archived": repo["isArchived"],
              "errors": [], "references": []}
    branch = (repo.get("defaultBranchRef") or {}).get("name")
    result["default_branch"] = branch
    if not branch:
        result["errors"].append("No default branch")
        return result
    try:
        head = gh("api", f"{prefix}/commits/{branch}")["sha"]
        result["head"] = head
        tree = gh("api", f"{prefix}/git/trees/{head}?recursive=1")
        if tree.get("truncated"):
            result["errors"].append("Repository tree truncated; inventory incomplete")
        paths = [entry["path"] for entry in tree["tree"] if entry["type"] == "blob"
                 and (entry["path"].startswith(".github/") or
                      entry["path"] in ("README.md", "THORNE_ENGINEERING_CUTOVER.md"))]
        import base64
        for path in paths:
            # Inspect callers/configuration, not the retained implementation/tests.
            if path.startswith(".github/actions/") or not path.endswith((".yml", ".yaml", ".md")):
                continue
            data = gh("api", f"{prefix}/contents/{path}?ref={head}")
            content = base64.b64decode(data["content"]).decode()
            hits = [{"line": n, "text": line.strip()} for n, line in enumerate(content.splitlines(), 1)
                    if any(term in line for term in ("thorne-pr-boundary-check", "DHF Trace",
                                                    "thorne-pr-verification-trace", "Safety Class"))]
            if hits:
                result["references"].append({"path": path, "matches": hits})
    except (RuntimeError, KeyError, ValueError) as error:
        result["errors"].append(str(error))
    for key, endpoint in (("effective_rules", f"{prefix}/rules/branches/{branch}"),
                          ("classic_protection", f"{prefix}/branches/{branch}/protection")):
        try:
            result[key] = gh("api", endpoint)
        except RuntimeError as error:
            result[key] = {"unavailable": str(error)}
            # A 404 may mean no classic protection OR insufficient access.
            # Keep it unresolved until the operator confirms which applies.
            result["errors"].append(f"{key}: {error}")
    return result


def main():
    repositories = gh("repo", "list", "eiro-inc", "--limit", "1000", "--json",
                      "name,isArchived,defaultBranchRef")
    if len(repositories) == 1000:
        raise RuntimeError("Repository limit reached; inventory may be incomplete")
    # Include every org repository: consumers are not limited to a thorne prefix.
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(capture, repositories))
    print(json.dumps({"captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      "repositories": results}, indent=2))


if __name__ == "__main__":
    main()
