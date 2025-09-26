// static/js/i18n.js
(function (global) {
  async function setLang(code) {
    try {
      const r = await fetch(`/api/translations/${encodeURIComponent(code)}`);
      const d = await r.json();
      if (!d.success) throw new Error(d.error || "translation fetch failed");
      applyI18n(d.translations || {});
    } catch (e) {
      console.warn("setLang failed", e);
    }
  }

  function applyI18n(map) {
    document.querySelectorAll("[data-i18n]").forEach((node) => {
      const k = node.getAttribute("data-i18n");
      if (k && map[k]) node.textContent = map[k];
    });
  }

  async function getPreferredLang() {
    // 1) localStorage (live preference across pages)
    const ls = localStorage.getItem("app.lang");
    if (ls) return ls;

    // 2) server settings (default)
    try {
      const rs = await fetch("/api/settings", {
        headers: { Accept: "application/json" },
      });
      const s = await rs.json();
      return (
        (s.settings && s.settings.language && s.settings.language.default) ||
        "en"
      );
    } catch {
      return "en";
    }
  }

  async function bootstrapLang() {
    const code = await getPreferredLang();
    await setLang(code);
  }

  // Allow other tabs to update immediately when language changes
  window.addEventListener("storage", async (e) => {
    if (e.key === "app.lang" && e.newValue) {
      await setLang(e.newValue);
    }
  });

  // Expose minimal API
  global.i18n = { setLang, applyI18n, bootstrapLang };
})(window);
