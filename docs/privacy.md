# Privacy Policy

*Last updated: May 2026*

---

## Summary

openstan does not collect, transmit, or store any personal data outside your own
machine. No account is required and no internet connection is needed to use the
application.

---

## Data storage

All data created by openstan — including imported bank statements, parsed
transactions, project configuration, and exported files — is written exclusively
to folders on your own device. You choose where each project folder is created.
openstan has no servers and no cloud storage. Your financial data never leaves
your machine.

---

## Network activity

openstan makes one outbound network request: an **update check on startup**.

When the application launches, it silently queries the
[GitHub Releases API](https://api.github.com/repos/boscorat/openstan/releases/latest)
to compare the installed version against the latest published release. If a newer
version is available, a dialog is shown offering a link to the release notes.

The request:

- Is made over HTTPS to `api.github.com`
- Sends only a standard HTTP `User-Agent: openstan` header
- Does **not** transmit any personal data, usage data, or information about your
  project files
- Fails silently if the network is unavailable — no error is shown and the
  application continues normally
- Does **not** download or install anything automatically; downloading an update
  is always a manual action by the user

No other network requests are made by openstan.

---

## Optional exchange rate data

openstan may in a future release offer an **opt-in** feature to retrieve currency
exchange rates from a third-party API. This feature:

- Is strictly optional and disabled by default — it will only make network
  requests if you explicitly enable it
- Will send only the currency codes required to fetch a rate (e.g. `GBP`, `USD`)
  — no personal data, transaction amounts, or account details are transmitted
- Will be clearly labelled in the application settings with a description of what
  data is sent and to which service

This section will be updated with the specific API provider and its privacy policy
when the feature is released.

---

## Telemetry and analytics

openstan contains no telemetry, crash reporting, usage analytics, or any other
background data collection.

---

## Third-party components

openstan uses open-source libraries (PyQt6, Polars, and others) as listed in the
project's [`pyproject.toml`](https://github.com/boscorat/openstan/blob/master/pyproject.toml).
None of these libraries are configured to collect or transmit data in the context
of openstan.

---

## Code signing

Windows installers are code-signed through [SignPath Foundation](https://signpath.org),
a non-profit organisation that provides free code signing for open-source projects.
The signing process does not involve any user data.

---

## Contact

If you have any questions about this policy, please open an issue on the
[GitHub repository](https://github.com/boscorat/openstan/issues).
