 document.addEventListener("DOMContentLoaded", () => {

  /* ---------- Floating left sidebar ---------- */
  try {
    const sidebar = document.querySelector(".floating-sidebar");
    const sidebarLinks = document.querySelectorAll(".sidebar-link");

    if (sidebar) {
      // The CSS hover state handles the normal reveal. This adds a forgiving
      // 30px activation area so moving to the left edge feels effortless.
      document.addEventListener("mousemove", (event) => {
        sidebar.classList.toggle("is-open", event.clientX <= 30);
      });

      sidebarLinks.forEach((link) => {
        link.addEventListener("click", (event) => {
          sidebarLinks.forEach((item) => item.classList.remove("active"));
          link.classList.add("active");

          const target = document.querySelector(link.getAttribute("href"));
          if (target) {
            event.preventDefault();
            target.scrollIntoView({ behavior: "smooth", block: "start" });
          }
        });
      });
    }
  } catch (err) {
    console.error("[foodtruth] floating sidebar setup failed:", err);
  }

  /* ---------- Hero laptop illustration ---------- */
  try {
    const heroArt = document.querySelector(".hero-laptop-art");
    if (heroArt) {
      const showHeroArt = () => heroArt.classList.add("is-ready");
      const hideHeroArt = () => heroArt.remove();

      if (heroArt.complete) {
        heroArt.naturalWidth ? showHeroArt() : hideHeroArt();
      } else {
        heroArt.addEventListener("load", showHeroArt, { once: true });
        heroArt.addEventListener("error", hideHeroArt, { once: true });
      }
    }
  } catch (err) {
    console.error("[foodtruth] hero illustration setup failed:", err);
  }

  /* ---------- Toggle: Enter Barcode vs Search Product ---------- */
  try {
    const modeBarcodeBtn = document.getElementById("mode-barcode");
    const modeSearchBtn = document.getElementById("mode-search");
    const barcodeRow = document.getElementById("barcode-row");
    const searchRow = document.getElementById("search-row");

    if (modeBarcodeBtn && modeSearchBtn && barcodeRow && searchRow) {
      function setMode(mode) {
        const isBarcode = mode === "barcode";
        modeBarcodeBtn.classList.toggle("active", isBarcode);
        modeSearchBtn.classList.toggle("active", !isBarcode);
        barcodeRow.style.display = isBarcode ? "flex" : "none";
        searchRow.style.display = isBarcode ? "none" : "flex";
      }
      modeBarcodeBtn.addEventListener("click", () => setMode("barcode"));
      modeSearchBtn.addEventListener("click", () => setMode("search"));
    } else {
      console.warn("[foodtruth] mode toggle elements missing", {
        modeBarcodeBtn, modeSearchBtn, barcodeRow, searchRow
      });
    }
  } catch (err) {
    console.error("[foodtruth] mode toggle setup failed:", err);
  }

  const scanForm = document.getElementById("scan-form");

  /* ---------- Auto-submit when a barcode image is chosen ---------- */
  try {
    const barcodeImageInput = document.getElementById("barcode_image");

    if (barcodeImageInput && scanForm) {
      barcodeImageInput.addEventListener("change", () => {
        if (barcodeImageInput.files && barcodeImageInput.files.length > 0) {
          scanForm.submit();
        }
      });
    } else {
      console.warn("[foodtruth] barcode image input or form missing", {
        barcodeImageInput, scanForm
      });
    }
  } catch (err) {
    console.error("[foodtruth] barcode image auto-submit setup failed:", err);
  }

  /* ---------- Product name autocomplete (/suggest) ---------- */
  try {
    const productInput = document.getElementById("product-name-input");
    const suggestionsBox = document.getElementById("suggestions");
    const barcodeHiddenInput = document.getElementById("barcode-input");

    console.log("[foodtruth] autocomplete init:", {
      productInput: !!productInput,
      suggestionsBox: !!suggestionsBox,
      barcodeHiddenInput: !!barcodeHiddenInput,
      scanForm: !!scanForm
    });

    if (productInput && suggestionsBox && barcodeHiddenInput && scanForm) {
      let debounceTimer = null;
      let activeController = null;

      productInput.addEventListener("input", () => {
        const query = productInput.value.trim();
        console.log("[foodtruth] typed:", query);
        clearTimeout(debounceTimer);

        if (query.length < 2) {
          suggestionsBox.style.display = "none";
          suggestionsBox.innerHTML = "";
          return;
        }

        debounceTimer = setTimeout(() => {
          if (activeController) activeController.abort();
          activeController = new AbortController();

          console.log("[foodtruth] fetching /suggest?q=" + query);

          fetch(`/suggest?q=${encodeURIComponent(query)}`, { signal: activeController.signal })
            .then((res) => {
              console.log("[foodtruth] /suggest response status:", res.status);
              return res.json();
            })
            .then((results) => {
              console.log("[foodtruth] /suggest results:", results);
              suggestionsBox.innerHTML = "";
              if (!results.length) {
                suggestionsBox.style.display = "none";
                return;
              }
              results.forEach((product) => {
                const item = document.createElement("div");
                item.className = "suggestion-item";

                const thumb = document.createElement("img");
                thumb.className = "suggestion-thumb";
                thumb.src = product.image || "/static/img/placeholder.png";
                thumb.alt = "";

                const text = document.createElement("div");
                text.className = "suggestion-text";
                const nameEl = document.createElement("span");
                nameEl.className = "suggestion-name";
                nameEl.textContent = product.name;
                text.appendChild(nameEl);
                if (product.brand) {
                  const brandEl = document.createElement("span");
                  brandEl.className = "suggestion-brand";
                  brandEl.textContent = product.brand;
                  text.appendChild(brandEl);
                }

                item.appendChild(thumb);
                item.appendChild(text);

                item.addEventListener("click", () => {
                  // Submit via the exact barcode rather than re-searching by
                  // name, so the product picked is guaranteed to be the one
                  // shown in the dropdown. app.py checks product_name first,
                  // so it must be cleared for the barcode branch to run.
                  barcodeHiddenInput.value = product.code;
                  productInput.value = "";
                  suggestionsBox.style.display = "none";
                  scanForm.submit();
                });

                suggestionsBox.appendChild(item);
              });
              suggestionsBox.style.display = "block";
            })
            .catch((err) => {
              if (err.name !== "AbortError") {
                console.error("[foodtruth] /suggest fetch failed:", err);
              }
              suggestionsBox.style.display = "none";
            });
        }, 250);
      });

      document.addEventListener("click", (e) => {
        if (!suggestionsBox.contains(e.target) && e.target !== productInput) {
          suggestionsBox.style.display = "none";
        }
      });
    } else {
      console.warn(
        "[foodtruth] autocomplete NOT active - one or more required elements " +
        "(#product-name-input, #suggestions, #barcode-input, #scan-form) is missing from this page."
      );
    }
  } catch (err) {
    console.error("[foodtruth] autocomplete setup failed:", err);
  }

  /* ---------- Colour the score pills based on grade / group ---------- */
  try {
    const gradeColors = {
      A: "#1fae5c", B: "#7ac043", C: "#f0b429", D: "#e8792c", E: "#e0473f"
    };
    const novaColors = {
      1: "#1fae5c", 2: "#7ac043", 3: "#e8792c", 4: "#e0473f"
    };

    document.querySelectorAll(".eco-pill, .nutri-pill").forEach((pill) => {
      const grade = (pill.dataset.grade || "").toUpperCase();
      if (gradeColors[grade]) pill.style.background = gradeColors[grade];
    });

    document.querySelectorAll(".nova-pill").forEach((pill) => {
      const group = pill.dataset.group;
      if (novaColors[group]) pill.style.background = novaColors[group];
    });
  } catch (err) {
    console.error("[foodtruth] score pill coloring failed:", err);
  }
});