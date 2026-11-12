# Issue Tracker: GitHub

Issues and specifications for this repository live in GitHub Issues on `Hgaines88/data-quest`.

## Safety Boundary

This clone has two remotes:

- `origin`: `Hgaines88/data-quest` - Hakeem's writable fork
- `upstream`: `rearc/data-quest` - the original assessment repository

Always pass `--repo Hgaines88/data-quest` to GitHub CLI issue commands because GitHub CLI may otherwise resolve the upstream repository. Never create, edit, label, close, or otherwise modify issues in `rearc/data-quest`.

Before the first issue write in a session, verify the target:

```bash
gh repo view Hgaines88/data-quest --json nameWithOwner,viewerPermission,hasIssuesEnabled
```

Proceed only when the result identifies `Hgaines88/data-quest` with write-capable permission.

## Conventions

- Create an issue with `gh issue create --repo Hgaines88/data-quest`.
- Read an issue with `gh issue view <number> --repo Hgaines88/data-quest`.
- List issues with `gh issue list --repo Hgaines88/data-quest` and appropriate state filters.
- Comment with `gh issue comment <number> --repo Hgaines88/data-quest`.
- Close an issue only after recording the completion evidence.
- Use GitHub's native issue dependencies when available.
- When native dependencies are unavailable, include a `Blocked by: #<number>` line in the issue body.
- A ticket is ready only when every blocking issue is closed.

## Skill Operations

When a skill says "publish to the issue tracker," create a GitHub issue in `Hgaines88/data-quest`.

When a skill says "fetch the relevant ticket," read the corresponding issue and its comments from `Hgaines88/data-quest`.

Pull requests are not a request or triage surface for this repository.
