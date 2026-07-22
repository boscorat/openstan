# Security & Privacy Guidelines

This project uses test data from bank statements to validate parsing and anonymisation functionality. We maintain strict security practices to protect user data and prevent accidental commits of sensitive information.

## Test Data Security

### Synthetic vs. Anonymised Test PDFs

This repository uses two types of test PDFs:

1. **Synthetic PDFs** (safe to commit)
   - Generated programmatically with fake data
   - No real customer information
   - Located in `tests/fixtures/pdfs/synthetic/`
   - Used in public CI/CD workflows
   - Fast and deterministic

2. **Anonymised PDFs** (private, fetched during CI)
   - Real bank statements with sensitive information removed
   - Stored in private repo (`bank-statement-data`)
   - Fetched automatically during CI testing (if SSH key available)
   - Never committed to public repositories
   - Automatically cleaned up after tests
   - Provides real-world format validation

### PDF Security Rules

❌ **Never commit**:
- Unanonymised PDFs (with real customer names, account numbers, etc.)
- PDFs with identifiable information
- PDFs from `tests/fixtures/pdfs/good/` or `pdfs/bad/` in public repos
- Files from private `bank-statement-data` repository

✅ **Safe to commit**:
- Synthetic PDFs in `tests/fixtures/pdfs/synthetic/`
- Test code and configuration
- Documentation

### Preventing Accidental PDF Commits

This repository includes protective measures:

1. **`.gitignore` rules**:
   ```gitignore
   # Block all PDFs by default
   *.pdf
   
   # Exception: Allow synthetic PDFs only
   !tests/fixtures/pdfs/synthetic/
   !tests/fixtures/pdfs/synthetic/**/*.pdf
   ```

2. **CI Cleanup**:
   - Anonymised PDFs are fetched to temporary locations (`/tmp`)
   - Automatically cleaned up after tests complete
   - Never persisted in checked-out code

3. **Git Protection**:
   - Pre-commit hooks can be configured to block PDF commits
   - Repository administrators review all contributions

## Binary Scanning with VirusTotal

### Automated Malware Scanning

All platform binaries (Linux .deb/.rpm, Windows .msi, macOS .dmg) are automatically scanned with **VirusTotal** before draft releases are promoted to published releases. VirusTotal aggregates results from 75+ antivirus engines to detect malware signatures and suspicious patterns.

#### How It Works

1. **Trigger**: When a version tag is pushed (e.g., `git tag v1.0.0`)
2. **Process**:
   - All four platform builds complete (Linux x86_64/ARM64, Windows, macOS)
   - **Each build job uploads binaries directly to a draft release** (draft is created immediately after builds complete)
   - The `scan-with-virustotal` job then downloads binaries from the existing draft release
   - Each binary is uploaded to VirusTotal's API
   - Results are polled for analysis completion (~30–60 seconds per file)
   - Per-engine detection results are logged
3. **Gate**: If any binary is flagged with malicious detections, the `scan-with-virustotal` job fails. The draft release exists (created during builds) but remains unpublished—invisible to end users. Maintainers must resolve the issue, delete the draft, and re-tag to retry.
4. **Audit**: Detailed scan results are logged in GitHub Actions for maintainer review

#### False Positive Policy

VirusTotal results are interpreted using a graduated policy:

| Detection Type | Threshold | Action |
|---|---|---|
| **Malicious** (known malware name) | Any count | ❌ **BLOCK** — Release fails immediately |
| **Suspicious** (heuristic flags) | Any count | ⚠️ **WARN & LOG** — Release proceeds; logged for transparency |
| **Undetected** | N/A | ✅ **PASS** — Binary is clean |

**Plain English explanation:**

- **Malicious detections** are named malware signatures (e.g., "Win32.Emotet", "Trojan.Downloader"). These indicate real threats and must be investigated before release.
- **Suspicious detections** are heuristic rules (e.g., "Heur/Suspicious.Gen", "PUA.Installer.Suspicious"). These are common for legitimate installers (cx_Freeze, WiX unpack files to temporary directories, modify registry, etc.) and do not block release.

#### If a Scan Fails

| Scenario | Action |
|---|---|
| **Malicious detection found** | The draft release exists but is unpublished (invisible to users). Delete the draft, fix the binary, rebase, and re-tag. See RELEASE.md troubleshooting for cleanup steps. |
| **Network timeout** | Curl retries transient failures automatically. If all retries fail, re-run from the GitHub Actions UI. |
| **API key missing** | Add `VIRUSTOTAL_API_KEY` to repository secrets (admin only). |
| **VirusTotal service down** | Rare (~99.9% uptime). Wait and re-run, or temporarily disable scanning. |

**Note:** Because the draft remains unpublished, no user-facing binaries are exposed, but the draft must be cleaned up before retrying the release.

#### Investigating Detections Manually

1. Copy the binary's SHA256 hash from GitHub Actions logs
2. Go to https://www.virustotal.com/gui/home/upload
3. Paste the hash to view the full report
4. Review per-engine results to understand which engines flagged and why
5. Report false positives directly to affected vendors (not VirusTotal)

#### Allowed False Positives (Heuristic Exemptions)

If a single antivirus engine repeatedly flags a legitimate binary with heuristic rules:

1. **First occurrence**: Documented in GitHub issue
2. **Repeated occurrence**: File a request with the vendor for hash whitelisting
3. **Persistent false positives**: Add to allow-list in the scanning job (requires code change + review)

Example allow-list entry (if needed):
```bash
# Allow heuristic detections from specific vendors on specific platforms
# Format: ENGINE=DETECTION;PLATFORM
bitdefender=Heur/Suspicious.Gen;windows
```

---

## Credential & Secret Handling

### GitHub Secrets Used

This project uses GitHub Secrets for sensitive configuration:

- `SSH_PRIVATE_KEY_TEST_DATA` - SSH key for cloning private `bank-statement-data` repo (CI only)
  - Auto-masked in logs
  - Automatically deleted after use
  - Only available to administrators

- `VIRUSTOTAL_API_KEY` - API key for VirusTotal malware scanning (release workflow only)
  - Auto-masked in logs
  - Only used in release.yml (not in CI/CD for PRs)
  - Free tier account at https://www.virustotal.com
  - Should be rotated every ~90 days

### Best Practices

✅ **Do**:
- Use GitHub Secrets for sensitive configuration
- Rotate credentials regularly
- Review CI/CD logs for accidental exposure
- Investigate any release workflow failures related to scanning

❌ **Never**:
- Hardcode credentials in source code
- Commit `.env` files with secrets
- Share SSH private keys or API keys
- Include tokens in repository URLs
- Manually override VirusTotal detections without investigation

## CI/CD Security

### Anonymised PDF Fetch (CI Only)

During CI testing, the workflow optionally fetches anonymised PDFs from the private repo:

1. **Conditional fetch**: Only runs if `SSH_PRIVATE_KEY_TEST_DATA` secret is configured
2. **Graceful fallback**: Tests continue with synthetic PDFs if fetch fails
3. **Automatic cleanup**: PDFs are deleted after tests complete
4. **Private logs**: GitHub Actions logs are visible only to administrators

Example workflow step:
```yaml
- name: Fetch anonymised PDFs for testing (graceful fallback)
  id: fetch_anonymised
  continue-on-error: true
  env:
    SSH_PRIVATE_KEY_TEST_DATA: ${{ secrets.SSH_PRIVATE_KEY_TEST_DATA }}
  run: |
    # Check if secret is available (cannot use secrets directly in if: conditions)
    if [ -z "$SSH_PRIVATE_KEY_TEST_DATA" ]; then
      echo "secret not set - skipping PDF fetch"
      exit 0
    fi
    
    # Configure SSH with temporary deploy key
    mkdir -p ~/.ssh
    printf '%s\n' "$SSH_PRIVATE_KEY_TEST_DATA" > ~/.ssh/bank_statement_deploy_key
    chmod 600 ~/.ssh/bank_statement_deploy_key
    # ... SSH config setup ...
    
    # Clone PDFs via sparse checkout
    git clone --depth 1 --filter=blob:none --sparse \
      git@github.com:boscorat/bank-statement-data.git /tmp/test_pdfs
    
    # Populate bsp's cache directory for TestHarness
    mkdir -p ~/.cache/bank_statement_data/pdfs
    cp -r /tmp/test_pdfs/pdfs/good ~/.cache/bank_statement_data/pdfs/
    cp -r /tmp/test_pdfs/pdfs/bad ~/.cache/bank_statement_data/pdfs/
    mkdir -p ~/.cache/bank_statement_data/repo/.git
    
    # Create symlinks for conftest's "anonymised" mode detection
    mkdir -p tests/fixtures/pdfs
    ln -s /tmp/test_pdfs/pdfs/good tests/fixtures/pdfs/anonymised_good
    ln -s /tmp/test_pdfs/pdfs/bad tests/fixtures/pdfs/anonymised_bad
    
    echo "success=true" >> "$GITHUB_OUTPUT"

### Log Review

GitHub Actions logs are private and visible only to repository administrators. To audit logs for security:

1. Go to Actions → Select workflow run → View logs
2. Check for:
   - ❌ Unmasked SSH keys (should see `***`)
   - ❌ Exposed file paths or repository URLs
   - ❌ Error messages revealing sensitive data

## User Data & Submissions

### Using Private Test Data

If you have access to the private `bank-statement-data` repository:

1. **Setup local testing** (optional, for contributors with access):
   ```bash
   git clone git@github.com:boscorat/bank-statement-data.git ../bank-statement-data

   ln -s ../bank-statement-data/pdfs/good tests/fixtures/pdfs/anonymised_good
   ln -s ../bank-statement-data/pdfs/bad tests/fixtures/pdfs/anonymised_bad
   ```

2. **Run tests**:
   ```bash
   # Full suite (integration tests now run with anonymised PDFs)
   uv run python scripts/test_runner.py all

   # Unit tests only (no PDFs needed)
   uv run python scripts/test_runner.py unit
   ```

3. **Results are private** - Don't commit the cloned PDFs or symlinks

### Reporting Issues with Real Data

If you discover parsing issues with real bank statements:

1. **Anonymise the statement** using guidelines from private repo
2. **Submit via GitHub Issue** with anonymised attachment
3. **Or** create a PR to the private repo with anonymised PDF
4. Project maintainers will verify and add to test suite

See the private repo's [`ANONYMISATION_CHECKLIST.md`](https://github.com/boscorat/bank-statement-data/blob/master/ANONYMISATION_CHECKLIST.md) for anonymisation guidelines.

## Incident Response

### If Sensitive Data is Accidentally Committed

1. **Do not push** if you haven't pushed yet
2. **Amend the commit**:
   ```bash
   # Remove the sensitive file
   git rm --cached <sensitive_file>
   echo "<sensitive_file>" >> .gitignore
   git add .gitignore
   git commit --amend --no-edit
   ```

3. **If already pushed**:
   - Contact repository maintainers immediately
   - Use `BFG` or `git-filter-repo` to remove from history
   - Force push is required (uses `--force`)

4. **For leaked credentials**:
   - Revoke immediately
   - Rotate secrets
   - Notify all maintainers

## Questions?

- **Test data questions** → See [`TESTING.md`](TESTING.md)
- **PDF anonymisation** → See private repo: [`bank-statement-data/ANONYMISATION_CHECKLIST.md`](https://github.com/boscorat/bank-statement-data)
- **Security concerns** → Contact maintainers directly (not via Issues)
- **General contribution** → See [`CONTRIBUTING.md`](CONTRIBUTING.md)

## Summary

✅ **Safe practices**:
- Use synthetic PDFs for testing
- `.gitignore` protects against accidental commits
- CI automatically cleans up anonymised PDFs
- GitHub Secrets protect credentials

❌ **Never**:
- Commit unanonymised PDFs
- Hardcode credentials
- Skip anonymisation when submitting real data
- Share SSH keys

🛡️ **Security-first approach**:
- Multi-layer protection (`.gitignore` + CI cleanup + pre-commit checks)
- Audit trail and transparency
- Private repo for sensitive data
- Graceful fallback to synthetic PDFs
