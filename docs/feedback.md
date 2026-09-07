---
description: "Help improve openstan — share your experience with installation, imports, exports, and what features you would like to see next."
---

# Feedback

We would love to hear about your experience with openstan. Your feedback helps us
prioritise bug fixes and new features.

This form is **anonymous by default**. You can optionally provide an email
address if you are happy for us to contact you for follow-up.

---

<iframe
  id="openstan-feedback-ejuved"
  src="https://opnform.com/forms/openstan-feedback-ejuved?embed=true"
  style="border:none;width:100%;min-height:700px;"
  loading="lazy"
  title="openstan feedback form"
  referrerpolicy="no-referrer"
  sandbox="allow-forms allow-scripts allow-same-origin"
></iframe>
<script src="https://opnform.com/widgets/opnform-sdk.min.js"></script>
<script>
(function () {
  function schemeElement() {
    if (document.body && document.body.hasAttribute("data-md-color-scheme")) {
      return document.body;
    }
    return document.documentElement;
  }

  function syncDarkMode() {
    var el = schemeElement();
    var isDark = el.getAttribute("data-md-color-scheme") === "slate";

    if (!window.opnform || typeof window.opnform.get !== "function") {
      return;
    }

    var form = window.opnform.get("openstan-feedback-ejuved");
    if (form && typeof form.setDarkMode === "function") {
      form.setDarkMode(isDark);
    }
  }

  syncDarkMode();

  if (window.opnform && typeof window.opnform.once === "function") {
    window.opnform.once("ready", syncDarkMode);
  }

  new MutationObserver(syncDarkMode).observe(schemeElement(), {
    attributes: true,
    attributeFilter: ["data-md-color-scheme"],
  });
})();
</script>
