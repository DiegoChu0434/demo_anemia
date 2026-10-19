(function () {
  const KEY = "ac_tema";
  const root = document.documentElement;
  const btn = document.getElementById("themeToggle");
  const icon = document.getElementById("themeIcon");

  function aplicar(tema) {
    if (tema === "dark") {
      root.setAttribute("data-theme", "dark");
      if (icon) icon.textContent = "☀️";
      if (btn) btn.title = "Cambiar a modo claro";
    } else {
      root.removeAttribute("data-theme");
      if (icon) icon.textContent = "🌙";
      if (btn) btn.title = "Cambiar a modo oscuro";
    }
  }

  let guardado = "light";
  try { guardado = localStorage.getItem(KEY) || "light"; } catch (e) {}
  aplicar(guardado);

  if (btn) {
    btn.addEventListener("click", () => {
      const actual = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
      const nuevo = actual === "dark" ? "light" : "dark";
      aplicar(nuevo);
      try { localStorage.setItem(KEY, nuevo); } catch (e) {}
    });
  }
})();
