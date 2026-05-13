# openstan

**openstan** is a free, open-source desktop application for importing, organising, and analysing
your bank statements — no Python or database knowledge required. All data is stored locally on
your own machine; no account or internet connection is needed.

[![Import results — light](assets/screenshots/statement_results.png#only-light)](assets/screenshots/statement_results.png)
[![Import results — dark](assets/screenshots/dark/statement_results.png#only-dark)](assets/screenshots/dark/statement_results.png)

## What openstan does

- **Import** bank statement PDFs from any supported bank — one file at a time or whole folders at once.
- **Review** import results: successful statements are committed to your project database; statements that need attention are highlighted for review with full debug output.
- **Summarise** your project: see transaction counts, account breakdowns, and automatic detection of statement coverage gaps.
- **Export** your data to Excel, CSV, or JSON — either as a flat table or a full star-schema dataset.
- **Build reports** with a no-code report builder: filter, group, and aggregate your transactions, then export or preview them live.

---

## How to get started

1. [Install openstan](installation.md) for your operating system.
2. Follow the [Quick Start guide](quickstart.md) to create your first project and import your first statements.
3. Browse the [Screens](screens/project-management.md) section for a comprehensive guide to every panel and option.

---

## Supported banks

openstan parses statements using the [bank_statement_parser](https://boscorat.github.io/bank_statement_parser/)
library. The following banks and account types are currently supported:

| Bank | Supported account types |
|---|---|
| **HSBC UK** | Bank Account (Current), HSBC Advance, Flexible Saver, Online Bonus Saver, Rewards Credit Card |
| **TSB UK** | Spend & Save (Current Account) |
| **NatWest UK** | *(coming soon)* |

For the authoritative and up-to-date list, see the
[bank_statement_parser supported banks](https://boscorat.github.io/bank_statement_parser/#supported-banks-and-accounts)
documentation.

Additional banks can be added by creating a TOML configuration file — see the
[Adding a new bank](https://boscorat.github.io/bank_statement_parser/guides/new-bank-config/)
guide in the bank_statement_parser docs. If you'd prefer to request support rather than
configure it yourself, open a
[new bank request](https://github.com/boscorat/bank_statement_parser/issues/new?template=new-bank-request.yml)
on the bank_statement_parser issue tracker.

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
