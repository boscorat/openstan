# openstan — Free UK Bank Statement Analyser

**Parse, analyse, and export your UK bank statement PDFs in seconds.**  
Free, open source, and 100% offline — your data never leaves your machine.

> "I built openstan because I was manually typing HSBC statements into spreadsheets for my self-assessment tax return. There had to be a better way."  
> — Jason Farrar, creator

Import an entire year of statements, build reports, and export to Excel in under a minute. No subscription. No account. No internet connection required. No Python or database knowledge needed.

[![Import results — light](assets/screenshots/statement_results.png#only-light)](assets/screenshots/statement_results.png)
[![Import results — dark](assets/screenshots/dark/statement_results.png#only-dark)](assets/screenshots/dark/statement_results.png)

---

## Why openstan?

| | **openstan** | **EasyBankConvert** | **DocuClipper** | **Dext / AutoEntry** |
|---|---|---|---|---|
| **Price** | Free | $49–$159/month | $20–$360+/month | £25–£50+/month |
| **Privacy** | 100% offline | Cloud upload | Cloud upload | Cloud upload |
| **UK banks** | HSBC, TSB, NatWest + extensible | Implied (AI-based) | Explicitly yes | Yes |
| **Output** | Excel, CSV, JSON | Excel, CSV, JSON | Excel, CSV, QBO, Xero | Xero, QuickBooks, CSV |
| **Open source** | Yes (GPL-3.0) | No | No | No |
| **Extensible** | Yes — TOML files | No | No | No |
| **Offline** | Yes | No | No | No |

---

## What openstan does

- **Import** bank statement PDFs from any supported bank — one file at a time or whole folders at once.
- **Review** import results: successful statements are committed to your project database; statements that need attention are highlighted with full debug output and the original PDF side by side.
- **Summarise** your project: transaction counts, account breakdowns, and automatic detection of statement coverage gaps (missing months flagged clearly).
- **Export** to Excel, CSV, or JSON — either as a flat transactions table or a full star-schema dataset (accounts, calendar, statements, transactions, balances, gaps).
- **Build reports** with a no-code report builder: filter, group, and aggregate your transactions, save named configurations, and export results.
- **Advanced export** — spec-driven custom exports via TOML files with per-account and date-range filtering.

---

## Privacy

openstan makes **one outbound network call**: a silent version check on startup. No statement data, no telemetry, no analytics, no account registration. See the full [Privacy Policy](privacy.md).

Your bank statements are sensitive. They stay on your machine.

---

## Supported banks

openstan parses statements using the [bank_statement_parser](https://boscorat.github.io/bank_statement_parser/) library. The following banks and account types are currently supported:

| Bank | Supported account types |
|---|---|
| **HSBC UK** | Bank Account (Current), HSBC Advance, Flexible Saver, Online Bonus Saver, Rewards Credit Card |
| **TSB UK** | Spend & Save (Current Account) |
| **NatWest UK** | Current Account |

New banks can be added by anyone via a [TOML configuration file](https://boscorat.github.io/bank_statement_parser/guides/new-bank-config/) — no coding required. Don't see your bank? [Request it here](https://github.com/boscorat/bank_statement_parser/issues/new?template=new-bank-request.yml).

---

## How to get started

1. [Install openstan](installation.md) for your operating system — no Python required.
2. Follow the [Quick Start guide](quickstart.md) to create your first project and import your first statements.
3. Browse the [Screens](screens/project-management.md) reference for a guide to every panel and option.

---

## Supported platforms

| Platform | Installer |
|---|---|
| Windows 10 / 11 | `.msi` |
| macOS 12+ (Intel & Apple Silicon) | `.dmg` |
| Ubuntu / Debian | `.deb` |
| Fedora / RHEL | `.rpm` |

---

## Licence

openstan is released under the [GPL-3.0-or-later](https://www.gnu.org/licenses/gpl-3.0.html) licence.  
Copyright © 2025 Jason Farrar.
