---
name: release
description: Tag and publish a Pixel Buddy release. Use when the user asks to cut a release, bump the version, tag, or publish a new version (e.g. "release 0.3.0", "create a release", "tag and push").
disable-model-invocation: true
argument-hint: "[version | patch | minor | major]"
---

# Release Pixel Buddy

Pushing a `v*` tag triggers `.github/workflows/release.yml` (windows-latest). It builds with `packaging/build.ps1` (PyInstaller + Inno Setup), then creates the GitHub release if needed and uploads `PixelBuddy-Setup.exe` and `PixelBuddy-win64.zip`. Do not build or upload by hand unless Actions is unavailable.

The version lives in two places and they must match:
- `pixel_buddy/__init__.py` -> `__version__ = "X.Y.Z"`
- `packaging/PixelBuddy.iss` -> `#define AppVersion "X.Y.Z"` (default only; CI overrides it from the tag)

## Steps

1. **Preconditions.** Run `git status --short` and `git branch --show-current`. Must be on `main` with a clean tree and up to date (`git pull --ff-only`). If not, stop and tell the user.
2. **Pick the version.** Current: `git describe --tags --abbrev=0` and `__version__`. Argument can be an explicit `X.Y.Z` or `patch|minor|major`. If missing, look at `git log <last-tag>..HEAD --oneline` and propose a bump (fix -> patch, feat -> minor); ask the user to confirm. The tag `vX.Y.Z` must not already exist (`git tag -l`, `git ls-remote --tags origin`). Never move or delete an existing tag unless the user explicitly asks.
3. **Bump** both version locations. Preserve file encoding/BOM and line endings (use `sed -i` or Edit; do not rewrite the files).
4. **Commit and tag.**
   ```
   git add pixel_buddy/__init__.py packaging/PixelBuddy.iss
   git commit -m "chore: bump version to X.Y.Z"
   git tag -a vX.Y.Z -m vX.Y.Z
   ```
   End the commit message with the Co-Authored-By line required by the session's attribution reminder.
5. **Push** (confirm with the user first if they did not already ask to publish): `git push origin main vX.Y.Z`.
6. **Watch the build.** `gh run list --limit 1` for the run id, then `gh run watch <id> --exit-status`. Takes about 2-3 minutes.
7. **Verify assets.** `gh release view vX.Y.Z --json url,assets -q '.url, (.assets[]|"\(.name) \(.size)")'` must list both `PixelBuddy-Setup.exe` and `PixelBuddy-win64.zip`.
8. **Report** the release URL and asset sizes. Offer to replace the auto-generated notes (`gh release edit vX.Y.Z --notes ...`) with a summary of `git log <prev-tag>..vX.Y.Z`.

## Failure handling

- Job fails in ~3s with "account is locked due to a billing issue": GitHub billing problem, not the workflow. Tell the user to fix github.com/settings/billing, then `gh run rerun <id>`.
- Build step fails: read `gh run view <id> --log-failed`, fix on `main`, then bump to the next patch version and tag again. Do not reuse a tag that already produced a public release.
- Release exists but has no assets: re-run the workflow (`gh run rerun <id>`); the upload step uses `--clobber`, so it is safe to repeat.
- Actions unavailable: `powershell -ExecutionPolicy Bypass -File packaging\build.ps1`, then `gh release create vX.Y.Z dist\PixelBuddy-Setup.exe --generate-notes`.
