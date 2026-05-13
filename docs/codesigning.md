# Code Signing Policy

Free code signing provided by [SignPath.io](https://signpath.io),
certificate by [SignPath Foundation](https://signpath.org).

---

## Scope

Windows installers (`.msi`) for openstan are code-signed using a certificate
issued to **SignPath Foundation** and provided to this project free of charge
under the [SignPath Foundation OSS programme](https://signpath.org).

The signature covers the MSI installer package. It confirms that the installer
was produced by an automated, verifiable build from the source code in this
repository.

---

## Team roles

This is a solo open-source project. All roles are held by the project maintainer.

| Role | Member | Responsibilities |
|---|---|---|
| **Committer** | [Jason Farrar](https://github.com/boscorat) | Merges changes to `master`; maintains source code and build scripts |
| **Reviewer** | [Jason Farrar](https://github.com/boscorat) | Reviews all pull requests before merge |
| **Approver** | [Jason Farrar](https://github.com/boscorat) | Approves each release for signing |

---

## Privacy

openstan does not collect personal data. The only outbound network request is a
silent update check on startup (HTTPS to `api.github.com`; no personal data
transmitted). Users can disable this in the application settings.

Full details: [Privacy Policy](privacy.md)

---

## Build and release process

1. A version tag (e.g. `v1.0.0`) is pushed to the GitHub repository.
2. The [GitHub Actions release workflow](https://github.com/boscorat/openstan/blob/master/.github/workflows/release.yml)
   runs automatically:
   - Dependencies are installed via `uv sync`
   - The application is frozen with cx_Freeze
   - The MSI installer is compiled with WiX v4
3. The resulting MSI is submitted to SignPath.io for signing.
4. The signed MSI is attached to the GitHub Release.

All build configuration is in the public repository. The release workflow and
WiX installer source (`packaging/windows/openstan.wxs`) are open to inspection.

---

## Reporting concerns

If you believe a signed openstan installer contains malware or violates the
SignPath Foundation code of conduct, please report it to
[support@signpath.io](mailto:support@signpath.io) and open an issue on the
[openstan issue tracker](https://github.com/boscorat/openstan/issues).
