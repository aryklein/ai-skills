---
name: update-aur-package
description: Update Arch/AUR PKGBUILD packages. Use when bumping pkgver, refreshing checksums, regenerating .SRCINFO, verifying sources, committing, or pushing AUR package updates.
---

# Update AUR Package

Use this workflow when updating an Arch Linux or AUR package repository that contains a `PKGBUILD`.

## Workflow

1. Inspect the package metadata first.

Read `PKGBUILD`, `.SRCINFO`, task files such as `Taskfile.yaml`, and any relevant project notes. Check recent commit history to learn the repository's commit message style.

2. Identify the new upstream release.

Confirm the version number, release URL, source asset name, signature asset name, and any published checksum or digest. Do not assume that upstream asset names stayed the same.

3. Update `PKGBUILD` minimally.

Set `pkgver` to the new upstream version. Keep `pkgrel=1` for a new upstream version unless the task is specifically a rebuild of the same upstream version. Update `source` only when the upstream asset naming scheme or hosting location changed.

4. Refresh checksums.

Prefer `updpkgsums` when available. If upstream publishes trusted asset digests, those may be used directly after confirming they match the exact source asset. Keep detached signature sums as `SKIP` when that is the existing package pattern.

5. Regenerate `.SRCINFO`.

Run:

```bash
makepkg --printsrcinfo > .SRCINFO
```

Never hand-edit `.SRCINFO` unless there is no working Arch packaging tool available.

6. Verify sources.

Run:

```bash
makepkg --verifysource
```

Report checksum failures, missing PGP keys, expired-key warnings, signature failures, or changed asset names clearly. A verified signature with an expired key is still a warning that should be surfaced to the user.

7. Review the diff.

Before committing, inspect:

```bash
git status --short
git diff
git log --oneline -10
```

Only stage intended files. For a normal version bump this is usually `PKGBUILD` and `.SRCINFO`.

8. Commit only when requested.

Use the repository's existing commit message style. Common AUR package styles include `New release: x.y.z`, `Update to x.y.z`, or `pkgver=x.y.z`.

9. Push only when requested.

Before pushing, confirm the current branch and remote. For AUR repositories this is commonly `master` and `ssh://aur@aur.archlinux.org/<package>.git`.

## Notes

- Do not add backward-compatibility code or package restructuring during a simple version bump.
- Do not reset, checkout, or revert unrelated user changes.
- If generated build artifacts appear in the worktree, do not include them unless the package intentionally tracks them.
- If `makepkg --verifysource` downloads sources, that is expected; avoid committing downloaded archives or extracted `src/` contents.
