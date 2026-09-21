---
description: "Contribute to openstan documentation. Guidelines for page structure, SEO best practices, frontmatter requirements, and design consistency."
---

# Contributing to Documentation

This guide covers standards and best practices for contributing to the openstan user guide. All documentation pages must follow these principles to maintain consistency, readability, and search engine visibility.

---

## Quick Checklist

Before submitting a documentation change, ensure:

- [ ] Frontmatter includes a **page-specific `description` field** (150–160 characters)
- [ ] `description` is unique and summarizes the page's value, not the site description
- [ ] Page has a single **H1 heading** (the title)
- [ ] Internal links use **relative paths** (e.g., `[link](../screens/export-data.md)`)
- [ ] All images have descriptive **alt text** and follow theme conventions (`#only-light` / `#only-dark` for theme-variant images)
- [ ] Code examples are clear, tested, and include language hints (` ```python `)
- [ ] Page is linked from at least one related page (internal linking for crawlability)

---

## Frontmatter & SEO

### Frontmatter Structure

Every documentation page **must** include frontmatter with a `description` field:

```yaml
---
description: "Import 12 months of bank statement PDFs, separate business from personal transactions, and export clean data for your Self Assessment tax return. 100% offline."
---

# Page Title
```

### Description Field Requirements

The `description` field is critical for SEO — it appears in:
- Google Search results (SERP snippets)
- Open Graph meta tags (social media previews)
- Twitter Card summaries (Twitter/X)

**Guidelines:**

- **Length:** 150–160 characters (Google shows 150–160 chars in search results)
- **Uniqueness:** Must be specific to the page, not the generic site description
- **Search intent:** Begin with action verbs or clear value propositions:
  - ✅ "Import 12 months of bank statement PDFs, separate business from personal..."
  - ✅ "Step-by-step guide to creating your first project, importing bank statements..."
  - ❌ "User guide for openstan — a desktop application..." (generic site description)
- **Keyword inclusion:** Naturally include 1–2 target keywords (not stuffed):
  - ✅ "Export committed transaction data to Excel, CSV, or JSON..."
  - ❌ "Export export export to Excel CSV JSON..."
- **Avoid:** Periods, promotional language ("Best!", "Amazing!"), or brand mentions unless necessary

**Examples:**

| Page | Good Description | Why |
|------|---|---|
| `/installation/` | "Install openstan on Windows, macOS, or Linux. Self-contained native installers — no Python required." | Clear value prop, search-friendly keywords (install, platforms) |
| `/use-cases/self-assessment/` | "Import 12 months of bank statement PDFs, separate business from personal transactions, and export clean data for your Self Assessment tax return. 100% offline." | Action-focused, includes search intent (self-assessment, bank statements) |
| `/screens/export-data/` | "Export committed transaction data from openstan to Excel, CSV, or JSON using configurable presets." | Specific outcome, formats listed |
| `/quickstart/` | "Step-by-step guide to creating your first project, importing bank statement PDFs, and exporting transactions in openstan." | Begins with intent, covers workflow |

---

## Page Structure

### Headings (H1, H2, H3)

- **H1 (one per page):** Page title, always auto-generated from frontmatter or Markdown H1
- **H2 (sections):** Major topic divisions
  - Nest logically; avoid skipping levels (H1 → H2 → H3, not H1 → H3)
  - Keep to 2–5 per page for readability
- **H3 (subsections):** Detail within major sections
  - Use sparingly; too many indicates content should be split across pages

**Example structure:**

```markdown
# Main Feature Title

## Overview / When to Use This

## Key Concepts or Prerequisites

### Sub-topic A

### Sub-topic B

## Step-by-Step Guide (if applicable)

## Common Issues & Troubleshooting

## Related Topics
```

### Content Flow

1. **Opening paragraph** (2–3 sentences):
   - Restate what the page is about (users skim)
   - Mention search keywords naturally
   - Link to related pages if needed

2. **Body sections**:
   - Use H2 for major topics
   - Start sections with brief intent statements
   - Include examples, screenshots, or code where helpful

3. **Closing**:
   - Optional: "See Also" or "Related Topics" section with 3–5 internal links
   - Links must use relative paths and point to `.md` files (MkDocs converts to URLs)

---

## Internal Linking

Internal links help Google crawl and understand your site structure. They also improve user navigation.

### Guidelines

- **Link frequently** (3–5 links per ~1,000 words is typical)
- **Use descriptive anchor text:** ❌ "Click here" → ✅ "Export Data" or "See the export guide"
- **Link to related pages:**
  - Use-case pages should link to relevant screen/feature pages
  - Screen pages should link back to use cases that use them
  - Sequential guides should link forward/backward
- **Use relative paths:** `[Export Data](../screens/export-data.md)` — MkDocs converts to URLs automatically
- **Avoid linking to the same page** (e.g., don't link to `/screens/export-data/` from within that same page)

**Example — Page Linking Map:**

```
/use-cases/self-assessment/
├─ Links to: /screens/export-data/ (to export for tax)
├─ Links to: /screens/run-reports/ (to build custom reports)
├─ Links to: ../index.md (back to all use cases)
└─ Links to: ../installation.md (getting started)
```

---

## Images & Screenshots

### Best Practices

- **Alt text:** Every image must have descriptive alt text (`![description](path)`)
  - ✅ "Project Management panel showing statement queue with 3 PDFs"
  - ❌ "screenshot" or leaving empty

- **Theme variants:** For light/dark theme screenshots, use fragment identifiers:
  ```markdown
  ![Alt text — light](assets/screenshots/foo.png#only-light)
  ![Alt text — dark](assets/screenshots/dark/foo.png#only-dark)
  ```
  - Light variants go in `assets/screenshots/`
  - Dark variants go in `assets/screenshots/dark/`
  - Zensical CSS hides the non-matching variant per user's theme

- **File size:** Optimize images before committing (compression, reasonable dimensions)

---

## Code Examples

- Use **language-specific code blocks:**
  ```python
  # Good
  def my_function():
      pass
  ```

  ```markdown
  # Avoid (no language hint)
  def my_function():
  ```

- **Testability:** Examples should be runnable (or clearly show what a user would do)
- **Comments:** Use inline comments to explain non-obvious logic
- **Syntax highlighting:** Ensure the language is specified for proper highlighting

---

## Writing Style

### Tone
- Clear, direct, and helpful
- Avoid jargon; explain technical terms on first use
- Write for UK English (e.g., "analyse" not "analyze")

### Common Patterns
- **Instructional:** "To import statements, click **Import** (Ctrl+I)..."
- **Conceptual:** "The Export Data panel separates committed transactions from queued imports..."
- **Cautionary:** "⚠️ Deleting a project cannot be undone."

### Formatting
- **Bold** for UI buttons/menu items: "Click **File** → **Export**"
- **Code font** for file paths, commands, config keys: `project.db`, `uv run openstan`
- **Monospace blocks** for terminal output or structured data
- **Admonitions** (if supported) for notes/warnings:
  ```markdown
  !!! note "Important"
      This is a note.

  !!! warning "Be careful"
      This is a warning.
  ```

---

## SEO Checklist Per Page

Use this when adding or updating a page:

| Item | Why | Action |
|------|-----|--------|
| **Unique description** | Improves SERP CTR and social previews | Add 150–160 char `description:` in frontmatter |
| **One H1** | Signals page topic to Google | Use page title as H1 |
| **H2/H3 hierarchy** | Google uses structure to understand content | Avoid skipping levels |
| **3–5 internal links** | Distributes authority, aids crawling | Link to 3–5 related pages using relative paths |
| **Image alt text** | Improves accessibility and image search | Every image has descriptive alt text |
| **Keyword natural language** | Avoids keyword stuffing penalties | Target keywords appear 1–2× naturally |
| **200+ words** | Gives Google enough content to rank | Short promotional pages won't rank well |
| **Related links section** | Keeps users on-site, improves crawl depth | Optional: "See Also" with 3–5 links at page end |

---

## Examples of Well-Structured Pages

### Excellent
- `/use-cases/self-assessment.md` — specific description, clear sections, internal links
- `/screens/export-data.md` — action-oriented, screenshots, step-by-step instructions
- `/installation.md` — platform-specific guidance, linked from multiple places

### Needs Improvement
- `docs/screens/about.md` — generic description, minimal content, no internal links
- `docs/feedback.md` — single paragraph, missing H2 sections

---

## Adding a New Page

### Steps

1. **Create the file** in the appropriate directory:
   - Use-case guides → `docs/use-cases/`
   - Feature/screen guides → `docs/screens/`
   - General info → `docs/`

2. **Add to `mkdocs.yml` nav:**
   ```yaml
   nav:
     - Screens:
         - Export Data: screens/export-data.md
         - New Feature: screens/new-feature.md  # ← add here
   ```

3. **Write with frontmatter:**
   ```yaml
   ---
   description: "150–160 character unique summary of page content."
   ---

   # Page Title

   Opening paragraph...
   ```

4. **Include internal links:**
   - Link from related pages back to your new page
   - Link from your new page to 3–5 existing related pages

5. **Test before committing:**
   ```bash
   uv run zensical build
   # Check site/your-new-page/index.html for correct og:description
   ```

6. **Verify sitemap:**
   - Run `uv run zensical build` and check `site/sitemap.xml`
   - Your new page should appear with `<url>https://openstan.org/your-new-page/</url>`

---

## Maintenance

- **Review quarterly:** Check for outdated information, broken links, or screenshots
- **Update descriptions when:** Page content significantly changes, new keywords are targeted
- **Test before deployment:** Always run `uv run zensical build` locally and inspect the generated HTML

---

## Questions?

Refer to `AGENTS.md` for project architecture and tech stack details. This guide covers documentation contribution standards only.

---

## Related Topics

- **[Community & Support](community.md)** – Connect with other contributors and users
- **[About Screen](screens/about.md)** – Attribution and license information
- **[Privacy Policy](privacy.md)** – Data handling standards
- **[GitHub Repository](https://github.com/boscorat/openstan)** – View source code and open issues
