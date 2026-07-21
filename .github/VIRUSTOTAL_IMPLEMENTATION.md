# VirusTotal Implementation Details

This document provides technical details for the VirusTotal scanning gate implemented in issue #74.

## Overview

The release workflow now includes an automated VirusTotal scanning job that:
- Runs after all 4 platform builds complete
- Scans all 6 binaries (Linux x86_64, Linux ARM64, Windows, macOS)
- Blocks releases if any binary has **malicious** detections
- Logs but allows **suspicious** (heuristic) detections
- Provides detailed per-engine results

## Architecture

```
Push version tag (e.g., v1.0.0)
        ↓
  ┌─────────────────────────────┐
  │ Parallel builds             │
  │ (Linux, Linux-ARM64,        │
  │  Windows, macOS)            │
  └─────────────────────────────┘
        ↓ (all succeed)
  ┌─────────────────────────────┐
  │ scan-with-virustotal job    │
  │ • Download binaries         │
  │ • Upload to VT API          │
  │ • Poll for completion       │
  │ • Parse results             │
  │ • Block on malicious        │
  │ • Allow on suspicious       │
  └─────────────────────────────┘
        ↓ (scan passes)
  ┌─────────────────────────────┐
  │ cleanup job                 │
  │ (strip old assets)          │
  └─────────────────────────────┘
```

## False Positive Policy (Reference)

### Policy Summary

| Detection Category | Definition | Action |
|---|---|---|
| **Malicious** | Known malware name (e.g., "Win32.Emotet", "Trojan.Downloader") | ❌ **BLOCK** release |
| **Suspicious** | Heuristic rule (e.g., "Heur/Suspicious.Gen", "PUA.Installer.Suspicious") | ⚠️ **LOG** but allow release |
| **Undetected** | Clean across all engines | ✅ **PASS** |

### Why Heuristics Are Allowed

Legitimate installers (cx_Freeze, WiX) perform actions that trigger heuristic detectors:
- Unpack files to temporary directories
- Modify Windows registry
- Inject into system paths
- Write to Program Files

These activities are normal for installers but resemble malware behavior to heuristic scanners.

### Handling False Positives

**First occurrence (single engine):**
- Log the detection
- Allow release to proceed
- Document in GitHub issue

**Repeated occurrence (multiple releases, same engine):**
- Contact the antivirus vendor (e.g., Kaspersky, BitDefender)
- Request hash whitelisting
- Provide vendor contact info and expected behaviors

**Persistent false positives:**
- Add to allow-list in the scanning job
- Requires code review before merge
- Must be documented with justification

### Allow-List Format

If a heuristic detection becomes persistent, edit the scanning job to add an exception:

```bash
# In .github/workflows/release.yml, scan-with-virustotal job:

# Allow specific heuristic detections
ALLOW_LIST="
bitdefender=Heur/Suspicious.Gen;windows
kaspersky=PUA.InstallersRisk;macos
"

check_allow_list() {
  local engine="$1"
  local detection="$2"
  local platform="$3"
  
  while IFS= read -r rule; do
    allowed_engine=$(echo "$rule" | cut -d= -f1)
    allowed_detection=$(echo "$rule" | cut -d= -f2 | cut -d; -f1)
    allowed_platform=$(echo "$rule" | cut -d; -f2)
    
    if [ "$engine" = "$allowed_engine" ] && \
       [ "$detection" = "$allowed_detection" ] && \
       [ "$platform" = "$allowed_platform" ]; then
      return 0  # Allowed
    fi
  done <<< "$ALLOW_LIST"
  
  return 1  # Not allowed
}
```

## Implementation Details

### Workflow Job: `scan-with-virustotal`

**Location:** `.github/workflows/release.yml` (lines 793–1014)

**Runs:** After builds succeed, before cleanup

**Inputs:** 
- Binaries downloaded from GitHub Release draft
- `VIRUSTOTAL_API_KEY` secret

**Outputs:**
- GitHub Actions logs with scan results
- Job exit code (0 = pass, 1 = fail)

### API Workflow

1. **Download binaries from release** (using `gh release download`)
   - Runs on ubuntu-latest (has `jq` and `curl` pre-installed)
   - Downloads all `.deb`, `.rpm`, `.msi`, `.dmg` files

2. **Upload to VirusTotal** (POST /files)
   - Curl uploads file with `x-apikey` header
   - Returns analysis ID

3. **Poll for completion** (GET /analyses/{id})
   - Polls every 1 second for up to 120 seconds
   - Typical completion: 30–60 seconds

4. **Fetch results** (GET /files/{sha256})
   - Parses `last_analysis_stats` for counts
   - Extracts per-engine results from `last_analysis_results`

5. **Log and decide**
   - Malicious > 0 → FAIL (exit 1)
   - Suspicious > 0 → WARN (log, exit 0)
   - Clean → PASS (exit 0)

### Error Handling

| Error | Behavior |
|---|---|
| Missing API key | Immediate failure with helpful message |
| Upload HTTP error | Count failure, continue scanning next binary |
| Polling timeout (>120s) | Count failure, move to next binary |
| API response parse error | Graceful fallback with partial info |
| Network timeout | Curl auto-retries with exponential backoff |

### Rate Limiting

VirusTotal free tier: 4 requests per minute

Current implementation:
- Uploads 6 files (6 requests)
- Polls ~10 times per file (60 requests worst-case)
- Fetches 6 final reports (6 requests)
- Total: ~72 requests spread over ~2–3 minutes
- **Safe** (within free tier limits)

Implementation includes 2-second sleep between files to stay conservative.

## Testing

### Local Testing (Before PR)

```bash
# Create VirusTotal account
curl https://www.virustotal.com/gui/home/upload

# Generate test file
echo "test" > /tmp/test.txt

# Export API key
export VIRUSTOTAL_API_KEY="your_api_key_here"

# Upload test file
curl -X POST \
  -H "x-apikey: ${VIRUSTOTAL_API_KEY}" \
  -F "file=@/tmp/test.txt" \
  https://www.virustotal.com/api/v3/files
```

### On-Fork Testing

1. Create test tag: `git tag v0.0.0-vt-test`
2. Push to fork: `git push origin v0.0.0-vt-test`
3. Watch release.yml run in GitHub Actions
4. Verify:
   - Scan job runs after builds
   - Binaries are downloaded
   - VirusTotal API responds
   - Results are logged
   - Cleanup job runs regardless

5. Delete test tag: `git tag -d v0.0.0-vt-test && git push origin --delete v0.0.0-vt-test`

### Production Testing (First Release)

1. Merge PR to main
2. Set `VIRUSTOTAL_API_KEY` secret in GitHub
3. Tag first release (e.g., `v0.2.0`)
4. Monitor Actions log
5. Verify no false positives block release
6. After scan passes, promote draft to published

## Maintenance

### Rotating API Key

VirusTotal recommends rotating keys every ~90 days:

1. Go to https://www.virustotal.com/gui/settings/api
2. Generate new key
3. Update GitHub Secret: Settings → Secrets and variables → Actions → VIRUSTOTAL_API_KEY
4. Delete old key from VirusTotal dashboard

### Monitoring Detections

After each release, review:
- GitHub Actions log for scan results
- Any new suspicious detections
- Patterns across releases

### Vendor Communications

If a vendor is repeatedly flagging legitimate binaries:

**Contact templates:**
- Kaspersky: support@kaspersky.com
- Bitdefender: submit@av-support.com
- Avast: submit@avast.com
- Microsoft Defender: antimalware_community@microsoft.com

**Request format:**
```
Subject: Hash whitelisting request - openstan release v1.0.0

Dear [Vendor],

We're maintaining an open-source desktop application (openstan) and have noticed 
your engine is flagging our legitimate Windows installer with heuristic detection: [DETECTION_NAME]

Binary: [BINARY_NAME]
SHA256: [SHA256_HASH]
Source: https://github.com/boscorat/openstan/releases/tag/v1.0.0
Legitimate use: Desktop GUI application using cx_Freeze/WiX packaging tools

Could you please whitelist this hash, or provide guidance on avoiding the heuristic?

Thank you,
[Your Name]
openstan maintainer
```

## Troubleshooting

### Release Failed with "Analysis failed"

**Cause:** VirusTotal returned an error status

**Fix:**
1. Check GitHub Actions log for HTTP response
2. Retry by deleting tag and re-pushing
3. If persistent, check VirusTotal dashboard for API issues

### Release Failed with "Polling timeout"

**Cause:** Binary took >2 minutes to analyze

**Fix:**
1. Increase `MAX_ATTEMPTS` in scan job (line ~875)
2. Manually verify on VirusTotal dashboard
3. If clean, document and monitor for pattern

### Suspicious Detection Blocking Release

**Note:** Suspicious detections should NOT block release. If they are:

1. Check the scanning job output
2. Verify detection count is actually in "suspicious" field
3. Review job logic (ensure `MALICIOUS > 0` is the block condition)
4. File GitHub issue with log details

### API Key Missing Error

**Cause:** `VIRUSTOTAL_API_KEY` secret not configured

**Fix:**
1. Create VirusTotal account (free): https://www.virustotal.com
2. Copy API key from https://www.virustotal.com/gui/settings/api
3. Add to GitHub repo: Settings → Secrets and variables → Actions → New secret
4. Name: `VIRUSTOTAL_API_KEY`
5. Retry release

## Related Files

- `.github/workflows/release.yml` - Main workflow with scan job
- `SECURITY.md` - Security policy and false positive handling
- `RELEASE.md` - Release documentation for users
- `AGENTS.md` - CI/CD configuration reference (links to this file)

## Questions?

For VirusTotal-specific issues:
- VirusTotal docs: https://developers.virustotal.com/v3.0/reference
- VirusTotal API reference: https://developers.virustotal.com/

For openstan-specific issues:
- File GitHub issue: https://github.com/boscorat/openstan/issues
- See `SECURITY.md` for complete policy
