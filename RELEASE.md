# Release Workflow & Promotion Checklist

## Overview

The `openstan` release process creates **draft releases** automatically via GitHub Actions when a version tag is pushed. Releases must be **manually promoted** from draft to published after verification and platform-specific checks.

This approach prevents premature publication while allowing time to:
- Verify all platform binaries are correct
- Submit Windows MSI to Microsoft WDSI portal for SmartScreen clearance
- Resolve any CI configuration issues without polluting the release history

---

## Quick Start: Create a Release

### 1. Ensure VirusTotal API Key is Configured

Before pushing a release tag, verify that the `VIRUSTOTAL_API_KEY` GitHub Secret is set:

1. Go to **GitHub** → **Settings** → **Secrets and variables** → **Actions**
2. Check that `VIRUSTOTAL_API_KEY` is present (value hidden)
3. If missing:
   - Create free account at https://www.virustotal.com/gui/home/upload
   - Copy API key from https://www.virustotal.com/gui/settings/api
   - Add to repository secrets

### 2. Push a version tag

```bash
git tag v1.2.3
git push origin v1.2.3
```

The tag must match the pattern `v*` (e.g. `v0.1.5`, `v1.0.0-rc1`). The workflow is triggered automatically.

### 2. Wait for builds to complete

All four platform jobs must complete successfully:
- Linux (.deb + .rpm)
- Linux ARM64 (_arm64.deb + .aarch64.rpm)
- Windows (.msi)
- macOS (.dmg)

**New:** After all builds complete, the **VirusTotal scanning job** runs automatically. This scans all 6 binaries against 75+ antivirus engines.

**Scanning can fail if:**
- Any binary is flagged with **malicious detections** (known malware names)
- Network errors occur during upload (curl retries transient failures automatically; otherwise re-run the workflow)

**Scanning succeeds if:**
- All binaries are clean (0 malicious detections)
- Binaries have only heuristic/suspicious flags (logged, but allowed)

If scanning fails:
- Check the GitHub Actions log for details
- Review the VirusTotal report at https://www.virustotal.com/gui/home/upload
- Fix the binary or wait for the issue to resolve, then re-push the tag
- See [SECURITY.md](SECURITY.md) for complete false positive policy

Monitor progress at: `https://github.com/boscorat/openstan/actions`

Build + scan time typically: **30–75 minutes** (varies by platform and VirusTotal queue)

### 3. Sign the Windows MSI

After VirusTotal scanning passes, sign the Windows `.msi` using jsign + SimplySign Desktop:

**Prerequisites:**
- SimplySign Desktop installed and running (`/opt/SimplySignDesktop/`)
- jsign JAR installed (`~/jsign/jsign.jar`)
- SunPKCS11 config at `~/provider_simplysign.cfg`
- SimplySign Desktop authenticated (Connect to SimplySign → OTP from Android app)

**Signing command:**
```bash
# Download the unsigned MSI from the draft release
gh release download v1.2.3 --pattern "*.msi" --dir ~/Downloads/

# Sign with jsign
~/jsign/jsign \
  --storetype PKCS11 \
  --keystore ~/provider_simplysign.cfg \
  --storepass "" \
  --alias 408B20EC00DECB005259B33D4EC0098A \
  --tsaurl http://time.certum.pl \
  --tsmode RFC3161 \
  ~/Downloads/openstan-1.2.3-Windows.msi

# Verify the signature
osslsigncode verify ~/Downloads/openstan-1.2.3-Windows.msi

# Re-upload the signed MSI to the draft release (replaces unsigned)
gh release upload v1.2.3 ~/Downloads/openstan-1.2.3-Windows.msi --clobber
```

---

## Release Promotion Checklist

Once all builds complete, the **draft release** will be created at:
`https://github.com/boscorat/openstan/releases`

Follow this checklist before promoting from draft to published:

### Pre-Publication Verification

- [ ] **All platform binaries attached**
  - [ ] `openstan-X.Y.Z-Linux-Ubuntu-x86_64.deb` (64-bit)
  - [ ] `openstan-X.Y.Z-Linux-Ubuntu-arm64.deb` (ARM64)
  - [ ] `openstan-X.Y.Z-Linux-Fedora-x86_64.rpm` (64-bit)
  - [ ] `openstan-X.Y.Z-Linux-Fedora-arm64.rpm` (ARM64)
  - [ ] `openstan-X.Y.Z-Windows.msi` (Windows)
  - [ ] `openstan-X.Y.Z-macOS.dmg` (macOS)

- [ ] **Release notes are present and accurate**
  - Describe key features, bug fixes, or changes
  - Include any known issues or breaking changes
  - Link to GitHub milestone/pull requests if applicable

- [ ] **macOS .dmg is notarised**
  - The workflow automatically handles code signing and Apple notarisation
  - No manual action needed — if the macOS build succeeded, it's notarised
  - Verify: Try opening the .dmg on a Mac; no Gatekeeper warnings should appear

- [ ] **Windows .msi is code-signed**
  - The MSI was signed with jsign + SimplySign Desktop (Certum OV certificate)
  - Verify: `osslsigncode verify <file>.msi` should show "Signature verification: ok"
  - Certificate: `CN=Open Source Developer Jason Telford Farrar` (Certum Code Signing 2021 CA)
  - Timestamp: Certum TSA (`http://time.certum.pl/`)

- [ ] **Windows .msi submission (WDSI portal)**
  - [ ] Go to https://www.microsoft.com/en-us/wdsi/filesubmission
  - [ ] Sign in with your Microsoft account
  - [ ] Select "Software" → "Incorrect detection" → "Clean software"
  - [ ] Upload the .msi file
  - [ ] **Allow 24–48 hours for Microsoft to review**
  - [ ] Once approved, SmartScreen warnings will be cleared
  
  *Note: This step is critical if the Windows installer is to be widely distributed. SmartScreen reputation builds over time with downloads; without WDSI submission, Windows may initially warn users about the unsigned binary.*

### No Breaking Changes?

- [ ] Review changelog for any API or UI breaking changes
  - If breaking changes are present, increment the **major** version
  - Otherwise, follow semantic versioning (minor for features, patch for fixes)
- [ ] All deprecation warnings added in previous releases are documented

---

## Manual Promotion: Draft → Published

Once the checklist is complete and Microsoft has cleared the .msi (if applicable):

### Option A: Using GitHub CLI

```bash
gh release edit v1.2.3 --draft=false
```

### Option B: Using GitHub Web UI

1. Go to `https://github.com/boscorat/openstan/releases`
2. Click on the draft release
3. Click **"Edit"** (pencil icon, top-right)
4. Uncheck **"This is a pre-release"** (if applicable)
5. Uncheck **"Set as a draft"** checkbox
6. Click **"Publish release"**

### Result

- Release is now **published** and visible to all users
- Appears on the **Releases** page as a normal (not draft) release
- May be tagged "Latest" if appropriate
- Announcement can be made on social media, blog, etc.

---

## Post-Publication

After publishing:

- [ ] The **cleanup job** automatically runs after all builds
  - Strips binaries from releases older than the **5 most recent**
  - Leaves a `NOTICE.txt` pointing users to the latest version
  - Keeps draft releases intact until they're manually promoted
  
- [ ] Announce the release (if desired)
  - GitHub Discussions
  - Project website
  - Social media
  - Email newsletter

---

## Troubleshooting

### Some platform jobs failed during build

- Check the failed job logs: `https://github.com/boscorat/openstan/actions`
- Common issues:
  - **macOS notarisation timeout**: Apple's service occasionally stalls; the workflow retries up to 75 minutes. If it fails, re-run the macOS job from GitHub Actions UI.
  - **Windows build timeout**: The WiX toolset can be slow; re-run if it hits the 30-minute timeout.
  - **Linux dependency issues**: Check if system libraries are out of date on the runner; typically resolves on next run.
- **Do not publish** if builds are incomplete — delete the partial draft release and push the tag again.

### Draft release is missing binaries

- Verify the tag matches the version in `pyproject.toml`
- Check individual job logs to see which platform failed
- Re-run failed jobs from the GitHub Actions UI
- Alternatively, delete the tag, fix the issue, and push a new tag

### Microsoft WDSI submission rejected

- Review Microsoft's feedback in the submission portal
- Common rejections: unsigned binary, wrong certificate, or binary has malware signatures (unlikely, but antivirus false positives happen)
- Resubmit or contact Microsoft support if clarification is needed
- Do **not** publish the release until WDSI clears it

### Release was published but should have been draft

You can revert a published release to draft:

```bash
gh release edit v1.2.3 --draft
```

This will immediately hide the release from the **Releases** page, but the tag and binaries remain.

### SimplySign Desktop not connecting

If SimplySign Desktop fails to connect:
1. Check the tray icon — it should show "Connected to SimplySign"
2. If disconnected, right-click tray → "Connect to SimplySign" → enter OTP from Android app
3. If the PKCS#11 module is not found, verify the library path: `/opt/SimplySignDesktop/SimplySignPKCS_64-MS-1.0.20.so`
4. Test certificate visibility: `keytool -list -keystore NONE -storetype PKCS11 -providerclass sun.security.pkcs11.SunPKCS11 -providerArg ~/provider_simplysign.cfg`

---

## Reference: Version Tags

- **Stable releases**: `v1.0.0`, `v1.2.3` — use semantic versioning
- **Release candidates**: `v1.0.0-rc1`, `v1.0.0-rc2` — include `-rc` suffix
- **Alpha/beta**: `v1.0.0-alpha1`, `v1.0.0-beta2` — include prefix and number
- **Development/test**: `v0.0.0-test` — for testing the release workflow only (delete tag after testing)

---

## Reference: Workflow Files

- **Main release workflow**: `.github/workflows/release.yml`
- **CI pipeline** (runs on all commits): `.github/workflows/ci.yml`
- **Cleanup** (strips old assets): `.github/workflows/release.yml` (cleanup job)

---

## Related Issues & Documentation

- **Issue #81**: Release workflow should create draft releases
- **Issue #76**: Review CI Release Pipeline (original checklist)
- **AGENTS.md**: Code signing setup (Certum + jsign, macOS Developer ID)
- **README.md**: Installation and user guide
