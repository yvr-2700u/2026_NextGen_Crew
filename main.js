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

  /* ---------- Language toggle (English / Hindi) ---------- */
  try {
    const translations = {
      nav_home: { en: "Home", hi: "होम" },
      nav_scan: { en: "Scan", hi: "स्कैन" },
      nav_categories: { en: "Categories", hi: "श्रेणियाँ" },
      nav_compare: { en: "Compare", hi: "तुलना करें" },
      nav_about: { en: "About", hi: "हमारे बारे में" },
      signin_btn: { en: "Sign In", hi: "साइन इन करें" },

      side_dashboard: { en: "Dashboard", hi: "डैशबोर्ड" },
      side_scan: { en: "Scan Product", hi: "उत्पाद स्कैन करें" },
      side_ai: { en: "AI Analysis", hi: "एआई विश्लेषण" },
      side_health: { en: "Health Score", hi: "हेल्थ स्कोर" },
      side_ingredients: { en: "Ingredients", hi: "सामग्री" },
      side_warnings: { en: "Warnings", hi: "चेतावनियाँ" },
      side_alt: { en: "Better Alternatives", hi: "बेहतर विकल्प" },
      side_compare: { en: "Compare Products", hi: "उत्पादों की तुलना करें" },
      side_buy: { en: "Where to Buy", hi: "कहाँ से खरीदें" },
      side_hint: { en: "Move to the left edge", hi: "बाएँ किनारे पर जाएँ" },

      hero_title: { en: "Making every food label meaningful", hi: "हर फ़ूड लेबल को सार्थक बनाना" },
      hero_subtext: {
        en: "Scan any barcode to get AI-powered insights on ingredients, health score, and smarter choices for you and your family.",
        hi: "सामग्री, हेल्थ स्कोर और आपके परिवार के लिए बेहतर विकल्पों की एआई-संचालित जानकारी पाने के लिए कोई भी बारकोड स्कैन करें।"
      },
      feat1_title: { en: "AI Ingredient Analysis", hi: "एआई सामग्री विश्लेषण" },
      feat1_desc: { en: "Understand every ingredient and what it means for you.", hi: "हर सामग्री को समझें और जानें कि इसका आपके लिए क्या मतलब है।" },
      feat2_title: { en: "Health Score (0–100)", hi: "हेल्थ स्कोर (0–100)" },
      feat2_desc: { en: "Get a quick health score to know how good your food is.", hi: "अपने भोजन की गुणवत्ता जानने के लिए तुरंत हेल्थ स्कोर पाएं।" },
      feat3_title: { en: "Better Alternatives", hi: "बेहतर विकल्प" },
      feat3_desc: { en: "Discover healthier options to make better choices.", hi: "बेहतर विकल्प चुनने के लिए स्वस्थ उत्पाद खोजें।" },

      mode_barcode: { en: "Enter Barcode", hi: "बारकोड दर्ज करें" },
      mode_search: { en: "Search Product", hi: "उत्पाद खोजें" },
      upload_barcode: { en: "Upload barcode", hi: "बारकोड अपलोड करें" },
      ph_barcode: { en: "Enter barcode number", hi: "बारकोड नंबर दर्ज करें" },
      ph_search: { en: "Search product by name", hi: "नाम से उत्पाद खोजें" },

      product_details: { en: "Product Details", hi: "उत्पाद विवरण" },
      label_name: { en: "Name:", hi: "नाम:" },
      label_brand: { en: "Brand:", hi: "ब्रांड:" },
      label_barcode: { en: "Barcode:", hi: "बारकोड:" },
      label_ecoscore: { en: "Eco-score:", hi: "इको-स्कोर:" },
      label_nutriscore: { en: "Nutri-Score:", hi: "न्यूट्री-स्कोर:" },
      label_nova: { en: "Nova-Group:", hi: "नोवा-समूह:" },

      explain_greenscore: {
        en: 'Green-Score is an experimental score that summarizes the environmental impacts of food products.',
        hi: "ग्रीन-स्कोर एक प्रायोगिक स्कोर है जो खाद्य उत्पादों के पर्यावरणीय प्रभावों को दर्शाता है।"
      },
      explain_grade: {
        en: "The score from A to E is calculated based on nutrients and foods to favor (proteins, fiber, fruits, vegetables and legumes) and nutrients to limit (calories, saturated fat, sugars, salt).",
        hi: "A से E तक का स्कोर पसंदीदा पोषक तत्वों (प्रोटीन, फाइबर, फल, सब्ज़ियाँ और दालें) और सीमित करने योग्य पोषक तत्वों (कैलोरी, संतृप्त वसा, शक्कर, नमक) के आधार पर तय होता है।"
      },
      explain_nova: {
        en: "Group 1 - Unprocessed or minimally processed foods<br>Group 2 - Processed culinary ingredient<br>Group 3 - Processed foods<br>Group 4 - Ultra-processed food and drink products",
        hi: "समूह 1 - असंसाधित या न्यूनतम संसाधित खाद्य पदार्थ<br>समूह 2 - संसाधित पाक सामग्री<br>समूह 3 - संसाधित खाद्य पदार्थ<br>समूह 4 - अति-संसाधित खाद्य एवं पेय उत्पाद"
      },

      nutrition_title: { en: "Nutrition (Per 100g)", hi: "पोषण (प्रति 100 ग्राम)" },
      nutr_calories: { en: "Calories", hi: "कैलोरी" },
      nutr_protein: { en: "Protein", hi: "प्रोटीन" },
      nutr_carbs: { en: "Carbs", hi: "कार्बोहाइड्रेट" },
      nutr_sugar: { en: "Sugar", hi: "शक्कर" },
      nutr_fat: { en: "Fat", hi: "वसा" },
      nutr_fiber: { en: "Fiber", hi: "फाइबर" },
      nutr_salt: { en: "Salt", hi: "नमक" },

      ingredients_title: { en: "Ingredients :", hi: "सामग्री :" },
      ingredients_unavailable: {
        en: "Plain-language explanation unavailable — set the GEMINI_API_KEY environment variable to enable it.",
        hi: "सरल भाषा में व्याख्या उपलब्ध नहीं है — इसे सक्षम करने के लिए GEMINI_API_KEY एनवायरनमेंट वेरिएबल सेट करें।"
      },

      health_title: { en: "♥ Health score (0–100)", hi: "♥ हेल्थ स्कोर (0–100)" },
      health_score_label: { en: "Health Score", hi: "हेल्थ स्कोर" },
      health_no_data: { en: "No Eco-Score, Nutri-Score, or NOVA data available for this product.", hi: "इस उत्पाद के लिए कोई इको-स्कोर, न्यूट्री-स्कोर या नोवा डेटा उपलब्ध नहीं है।" },
      health_empty: { en: "Scan or search a product to see its Health Score.", hi: "हेल्थ स्कोर देखने के लिए किसी उत्पाद को स्कैन या खोजें।" },
      health_banner: {
        en: "Our project combines the A-to-E Nutri-Score, environmental Eco-Score, and NOVA processing tiers into a single health rating. This unified score delivers a fast, comprehensive look at how a food product affects human biology and the planet. Users get an instant understanding of a food's nutritional value, sustainability, and industrial processing level.",
        hi: "हमारा प्रोजेक्ट A-से-E न्यूट्री-स्कोर, पर्यावरणीय इको-स्कोर और नोवा प्रोसेसिंग स्तरों को एक ही हेल्थ रेटिंग में जोड़ता है। यह एकीकृत स्कोर बताता है कि कोई खाद्य उत्पाद मानव शरीर और पृथ्वी को कैसे प्रभावित करता है। उपयोगकर्ताओं को उत्पाद के पोषण मूल्य, स्थिरता और प्रसंस्करण स्तर की तुरंत जानकारी मिलती है।"
      },

      warnings_intro: {
        en: "Nutrition Warning : The selected region shows a Nutrition Warning System table that provides an age-wise health analysis for the product",
        hi: "पोषण चेतावनी : चयनित क्षेत्र एक पोषण चेतावनी प्रणाली तालिका दिखाता है जो उत्पाद का आयु-वार स्वास्थ्य विश्लेषण प्रदान करती है"
      },
      warning_sys_title: { en: "Nutrition Warning System", hi: "पोषण चेतावनी प्रणाली" },
      warning_sys_subtitle: { en: "Age-wise Health Analysis", hi: "आयु-वार स्वास्थ्य विश्लेषण" },
      warning_product_label: { en: "Product :", hi: "उत्पाद :" },
      warning_col_nutrient: { en: "Nutrient", hi: "पोषक तत्व" },
      warning_col_children: { en: "Children (4-12)", hi: "बच्चे (4-12)" },
      warning_col_adults: { en: "Adults", hi: "वयस्क" },
      warning_col_elderly: { en: "Elderly (60+)", hi: "बुज़ुर्ग (60+)" },
      warning_col_diabetics: { en: "Diabetics", hi: "मधुमेह रोगी" },
      warning_banner: {
        en: "The table evaluates three key nutritional components—Sugar, Salt, and Saturated Fat—across four distinct demographic and health categories: Children (4–12), Adults, Elderly (60+), and Diabetics.",
        hi: "यह तालिका तीन प्रमुख पोषक तत्वों — शक्कर, नमक और संतृप्त वसा — का मूल्यांकन चार अलग-अलग आयु व स्वास्थ्य श्रेणियों में करती है: बच्चे (4–12), वयस्क, बुज़ुर्ग (60+) और मधुमेह रोगी।"
      },
      warnings_empty: { en: "Scan or search a product to see its age-wise nutrition warnings.", hi: "आयु-वार पोषण चेतावनियाँ देखने के लिए किसी उत्पाद को स्कैन या खोजें।" },

      alt_title: { en: "Healthier Alternative", hi: "स्वस्थ विकल्प" },
      alt_unavailable: {
        en: "Open Food Facts' product search is temporarily unavailable, so we couldn't look for a healthier alternative right now. Please try again shortly.",
        hi: "Open Food Facts की उत्पाद खोज अस्थायी रूप से उपलब्ध नहीं है, इसलिए हम अभी बेहतर विकल्प नहीं खोज सके। कृपया थोड़ी देर बाद पुनः प्रयास करें।"
      },
      alt_none_found: { en: "No suitable healthier alternative was found in this product's category on Open Food Facts.", hi: "Open Food Facts पर इस उत्पाद की श्रेणी में कोई उपयुक्त स्वस्थ विकल्प नहीं मिला।" },
      alt_empty: { en: "Scan or search a product to see a healthier alternative.", hi: "स्वस्थ विकल्प देखने के लिए किसी उत्पाद को स्कैन या खोजें।" },

      compare_title: { en: "Compare Product", hi: "उत्पादों की तुलना करें" },
      compare_col_nutrient: { en: "Nutrient", hi: "पोषक तत्व" },
      compare_col_scanned: { en: "Scanned Product", hi: "स्कैन किया गया उत्पाद" },
      compare_col_alt: { en: "Alternative", hi: "विकल्प" },
      compare_empty: { en: "A comparison will appear here once a healthier alternative is found.", hi: "स्वस्थ विकल्प मिलने पर यहाँ तुलना दिखाई देगी।" },

      purchase_title: { en: "🛒 Where to Buy", hi: "🛒 कहाँ से खरीदें" },
      buy_now_on: { en: "Buy Now on", hi: "अभी खरीदें" },
      not_on: { en: "Not on", hi: "यहाँ नहीं मिला" },
      try_these: { en: "? Try:", hi: "? इन्हें आज़माएं:" },
      cant_find: { en: "Still can't find it?", hi: "फिर भी नहीं मिला?" },
      find_online_btn: { en: "Find Online (Google Search)", hi: "ऑनलाइन खोजें (गूगल सर्च)" },
      purchase_empty: { en: "Scan or search a product to see where you can buy it.", hi: "यह कहाँ खरीदें यह देखने के लिए किसी उत्पाद को स्कैन या खोजें।" },

      side_about: { en: "About", hi: "हमारे बारे में" },
      about_title_1: { en: "About", hi: "" },
      about_title_2: { en: "FoodTruth", hi: "फ़ूडट्रुथ के बारे में" },
      about_text: {
        en: "FoodTruth is an AI-powered platform that helps you scan, analyze and understand food labels in simple language. We believe everyone deserves to know what's inside their food and make healthier choices for a better life.",
        hi: "फ़ूडट्रुथ एक एआई-संचालित प्लेटफ़ॉर्म है जो आपको फ़ूड लेबल स्कैन करने, उनका विश्लेषण करने और उन्हें सरल भाषा में समझने में मदद करता है। हमारा मानना है कि हर किसी को यह जानने का अधिकार है कि उनके भोजन में क्या है, ताकि वे बेहतर जीवन के लिए स्वस्थ विकल्प चुन सकें।"
      },
      about_devs_title: { en: "Meet the Developers", hi: "डेवलपर्स से मिलें" },
      about_contact_title: { en: "Get in Touch", hi: "संपर्क करें" },
      about_location: { en: "Nagpur, Maharashtra, India", hi: "नागपुर, महाराष्ट्र, भारत" },
      about_follow_title: { en: "Follow Us", hi: "हमें फॉलो करें" }
    };

    const langToggle = document.getElementById("lang-toggle");
    const STORAGE_KEY = "foodtruth-lang";

    function applyLanguage(lang) {
      document.querySelectorAll("[data-i18n]").forEach((el) => {
        const key = el.dataset.i18n;
        const entry = translations[key];
        if (entry && entry[lang]) el.innerHTML = entry[lang];
      });
      document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
        const key = el.dataset.i18nPlaceholder;
        const entry = translations[key];
        if (entry && entry[lang]) el.setAttribute("placeholder", entry[lang]);
      });
      document.documentElement.lang = lang;
      if (langToggle) {
        langToggle.querySelectorAll(".lang-option").forEach((btn) => {
          btn.classList.toggle("active", btn.dataset.lang === lang);
        });
      }
    }

    if (langToggle) {
      langToggle.querySelectorAll(".lang-option").forEach((btn) => {
        btn.addEventListener("click", () => {
          const lang = btn.dataset.lang;
          applyLanguage(lang);
          try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* ignore */ }
        });
      });
    }

    let savedLang = "en";
    try { savedLang = localStorage.getItem(STORAGE_KEY) || "en"; } catch (e) { /* ignore */ }
    if (savedLang === "hi") applyLanguage("hi");
  } catch (err) {
    console.error("[foodtruth] language toggle setup failed:", err);
  }
});
