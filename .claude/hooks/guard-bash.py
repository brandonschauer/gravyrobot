#!/usr/bin/env python3
"""PreToolUse guard for Bash: blocks destructive git/rm forms that prefix-based
permission rules miss (flags after the remote, combined short flags, `git -C`,
chained commands). Prints a permission decision as JSON; silent means no opinion."""
import json, re, shlex, sys

GIT_GLOBAL_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def segments(cmd):
    # Split chained/piped/substituted commands into individually checked pieces.
    return [s for s in re.split(r"&&|\|\||[;&|\n]|\$\(|`|\(|\)", cmd) if s.strip()]


def tokens(seg):
    try:
        toks = shlex.split(seg)
    except ValueError:
        toks = seg.split()
    # Drop leading env assignments and wrappers.
    while toks and (re.match(r"^\w+=", toks[0]) or toks[0] in ("sudo", "command", "env", "exec", "nohup", "time")):
        toks = toks[1:]
    return toks


def short_flags(args):
    return "".join(a[1:] for a in args if re.match(r"^-[A-Za-z]+$", a))


def check_git(args):
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if args[i] in GIT_GLOBAL_WITH_ARG else 1
    if i >= len(args):
        return None
    sub, rest = args[i], args[i + 1:]
    sf = short_flags(rest)

    if sub == "push":
        if any(a in ("--force", "--force-with-lease", "--force-if-includes", "--mirror", "--delete", "--prune") or a.startswith("--force-with-lease=") for a in rest) or "f" in sf or "d" in sf:
            return "deny", "Force/delete/mirror pushes rewrite or remove published history on the live site."
        if any(a.startswith("+") or (a.startswith(":") and len(a) > 1) for a in rest if not a.startswith("-")):
            return "deny", "`+ref` (force) and `:ref` (delete) refspecs rewrite or remove remote history."
    if sub == "reset" and "--hard" in rest:
        return "deny", "`git reset --hard` discards uncommitted work. Use `git stash` instead."
    if sub == "clean" and ("f" in sf or "--force" in rest):
        return "deny", "`git clean -f` permanently deletes untracked files (including local-only art)."
    if sub in ("checkout", "switch") and ("f" in sf or "--force" in rest or "--discard-changes" in rest):
        return "deny", "Forced checkout discards local changes."
    if sub in ("checkout", "restore") and "." in rest and "--staged" not in rest:
        return "deny", "Restoring `.` discards every uncommitted change in the tree."
    if sub == "branch" and ("D" in sf or ("--delete" in rest and "--force" in rest)):
        return "deny", "Force-deleting a branch can lose unmerged commits."
    if sub == "stash" and rest[:1] and rest[0] in ("drop", "clear"):
        return "deny", "Dropped stashes are hard to recover."
    if sub in ("filter-branch", "filter-repo"):
        return "deny", "History rewriting is off-limits for Claude."
    if sub == "reflog" and rest[:1] == ["expire"]:
        return "deny", "Expiring the reflog removes the safety net for recovery."
    if sub == "gc" and any(a.startswith("--prune") for a in rest):
        return "deny", "Pruning makes unreachable commits unrecoverable."
    if sub == "update-ref" and "d" in sf:
        return "deny", "Deleting refs directly bypasses git's safety checks."
    if sub == "add":
        if "f" in sf or "--force" in rest:
            return "deny", "`git add -f` bypasses .gitignore; anything committed here is public on the site."
        if any(a.rstrip("/").startswith("art-source") for a in rest):
            return "deny", "art-source/ is local-only full-size art and must never be committed."
    if sub == "commit" and "--amend" in rest:
        return "ask", "Amending rewrites the last commit; confirm it hasn't been pushed."
    if sub == "rebase":
        return "ask", "Rebasing rewrites history; confirm before running."
    return None


def check_rm(args):
    sf = short_flags(args)
    recursive = "r" in sf or "R" in sf or "--recursive" in args
    force = "f" in sf or "--force" in args
    if recursive and force:
        return "deny", "`rm -rf` is blocked. Delete specific files, or ask the user to do it."
    return None


def main():
    data = json.load(sys.stdin)
    cmd = (data.get("tool_input") or {}).get("command", "")
    for seg in segments(cmd):
        toks = tokens(seg)
        if not toks:
            continue
        prog = toks[0].rsplit("/", 1)[-1]
        verdict = check_git(toks[1:]) if prog == "git" else check_rm(toks[1:]) if prog == "rm" else None
        if verdict:
            decision, reason = verdict
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": decision,
                "permissionDecisionReason": f"guard-bash: {reason}",
            }}))
            return


if __name__ == "__main__":
    main()
