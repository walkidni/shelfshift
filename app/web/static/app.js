(() => {
  const config = window.ECT || {};
  const weightUnitAllowlist = config.weightUnitAllowlist || {};
  const weightUnitDefaults = config.weightUnitDefaults || {};
  const sourceWeightRequiredPlatforms = new Set(config.sourceWeightRequiredPlatforms || []);

  const _trimOrNull = (value) => {
    const text = String(value || "").trim();
    return text ? text : null;
  };

  const _splitCommaTokens = (value) => {
    const text = String(value || "").trim();
    if (!text) {
      return [];
    }
    const seen = new Set();
    const out = [];
    text.split(",").forEach((token) => {
      const cleaned = token.trim();
      if (!cleaned || seen.has(cleaned)) {
        return;
      }
      seen.add(cleaned);
      out.push(cleaned);
    });
    return out;
  };

  const _splitLines = (value) => {
    const text = String(value || "").trim();
    if (!text) {
      return [];
    }
    const seen = new Set();
    const out = [];
    text.split("\n").forEach((line) => {
      const cleaned = line.trim();
      if (!cleaned || seen.has(cleaned)) {
        return;
      }
      seen.add(cleaned);
      out.push(cleaned);
    });
    return out;
  };

  const _encodeJsonB64 = (obj) => {
    const json = JSON.stringify(obj);
    const bytes = new TextEncoder().encode(json);
    let binary = "";
    for (let i = 0; i < bytes.length; i += 1) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  };

  const syncWeightUnitSelect = (selectEl, platform) => {
    if (!selectEl) {
      return;
    }
    const allowedUnits = weightUnitAllowlist[platform] || [];
    const defaultUnit = weightUnitDefaults[platform] || allowedUnits[0] || "kg";
    const currentValue = selectEl.value;
    const selectedValue = allowedUnits.includes(currentValue) ? currentValue : defaultUnit;

    selectEl.innerHTML = "";
    allowedUnits.forEach((unit) => {
      const option = document.createElement("option");
      option.value = unit;
      option.textContent = unit.toUpperCase();
      if (unit === selectedValue) {
        option.selected = true;
      }
      selectEl.appendChild(option);
    });
  };

  const initUrlExportForm = () => {
    const targetPlatform = document.getElementById("target_platform");
    const weightUnit = document.getElementById("weight_unit");
    const bigcommerceFields = document.getElementById("bigcommerce-fields");
    const squarespaceFields = document.getElementById("squarespace-fields");
    if (!targetPlatform || !weightUnit || !bigcommerceFields || !squarespaceFields) {
      return;
    }

    const bigcommerceInputs = bigcommerceFields.querySelectorAll("select, input");
    const squarespaceInputs = squarespaceFields.querySelectorAll("input");

    const syncConditionalFields = () => {
      const platform = targetPlatform.value;
      syncWeightUnitSelect(weightUnit, platform);

      const showBigCommerceFields = platform === "bigcommerce";
      bigcommerceFields.classList.toggle("is-hidden", !showBigCommerceFields);
      bigcommerceFields.setAttribute("aria-hidden", showBigCommerceFields ? "false" : "true");
      bigcommerceInputs.forEach((input) => {
        input.disabled = !showBigCommerceFields;
      });

      const showSquarespaceFields = platform === "squarespace";
      squarespaceFields.classList.toggle("is-hidden", !showSquarespaceFields);
      squarespaceFields.setAttribute("aria-hidden", showSquarespaceFields ? "false" : "true");
      squarespaceInputs.forEach((input) => {
        input.disabled = !showSquarespaceFields;
      });
    };

    targetPlatform.addEventListener("change", syncConditionalFields);
    syncConditionalFields();
  };

  const initCsvImportForm = () => {
    const sourcePlatform = document.getElementById("source_platform");
    const sourceWeightFields = document.getElementById("source-weight-fields");
    const sourceWeightUnit = document.getElementById("source_weight_unit");
    if (!sourcePlatform || !sourceWeightFields || !sourceWeightUnit) {
      return;
    }

    const syncSourceWeightFields = () => {
      const required = sourceWeightRequiredPlatforms.has(sourcePlatform.value);
      sourceWeightFields.classList.toggle("is-hidden", !required);
      sourceWeightFields.setAttribute("aria-hidden", required ? "false" : "true");
      sourceWeightUnit.disabled = !required;
    };

    sourcePlatform.addEventListener("change", syncSourceWeightFields);
    syncSourceWeightFields();
  };

  const initCsvPreviewExportForm = () => {
    const previewTargetPlatform = document.getElementById("preview_target_platform");
    const previewWeightUnit = document.getElementById("preview_weight_unit");
    if (!previewTargetPlatform || !previewWeightUnit) {
      return;
    }

    const previewBigcommerceFields = document.getElementById("preview-bigcommerce-fields");
    const previewSquarespaceFields = document.getElementById("preview-squarespace-fields");
    const previewBigcommerceInputs = previewBigcommerceFields
      ? previewBigcommerceFields.querySelectorAll("select, input")
      : [];
    const previewSquarespaceInputs = previewSquarespaceFields
      ? previewSquarespaceFields.querySelectorAll("input")
      : [];

    const syncPreviewFields = () => {
      const platform = previewTargetPlatform.value;
      syncWeightUnitSelect(previewWeightUnit, platform);

      const showPreviewBigCommerce = platform === "bigcommerce";
      if (previewBigcommerceFields) {
        previewBigcommerceFields.classList.toggle("is-hidden", !showPreviewBigCommerce);
        previewBigcommerceFields.setAttribute("aria-hidden", showPreviewBigCommerce ? "false" : "true");
        previewBigcommerceInputs.forEach((input) => {
          input.disabled = !showPreviewBigCommerce;
        });
      }

      const showPreviewSquarespace = platform === "squarespace";
      if (previewSquarespaceFields) {
        previewSquarespaceFields.classList.toggle("is-hidden", !showPreviewSquarespace);
        previewSquarespaceFields.setAttribute("aria-hidden", showPreviewSquarespace ? "false" : "true");
        previewSquarespaceInputs.forEach((input) => {
          input.disabled = !showPreviewSquarespace;
        });
      }
    };

    previewTargetPlatform.addEventListener("change", syncPreviewFields);
    syncPreviewFields();
  };

  const initProductEditor = () => {
    const editor = document.querySelector("[data-product-editor]");
    if (!editor) {
      return;
    }

    const payloadScript = document.getElementById("editor-product-payload");
    if (!payloadScript) {
      return;
    }

    let payload;
    try {
      payload = JSON.parse(payloadScript.textContent || "{}");
    } catch {
      return;
    }
    if (!payload || typeof payload !== "object") {
      return;
    }

    const saveBtn = editor.querySelector("[data-action='save-product']");
    const status = editor.querySelector("[data-role='save-status']");
    const exportB64Input = document.querySelector(
      "form[action='/export-from-product.csv'] input[name='product_json_b64']",
    );
    if (!saveBtn || !exportB64Input) {
      return;
    }

    const getValue = (id) => {
      const el = editor.querySelector(`#${id}`);
      return el ? el.value : "";
    };

    const applyBasicEdits = () => {
      payload.title = _trimOrNull(getValue("edit_title"));
      payload.description = _trimOrNull(getValue("edit_description"));
      payload.vendor = _trimOrNull(getValue("edit_vendor"));
      payload.brand = _trimOrNull(getValue("edit_brand"));
      payload.tags = _splitCommaTokens(getValue("edit_tags"));

      payload.source = payload.source && typeof payload.source === "object" ? payload.source : {};
      payload.source.slug = _trimOrNull(getValue("edit_source_slug"));
      payload.source.url = _trimOrNull(getValue("edit_source_url"));

      payload.seo = payload.seo && typeof payload.seo === "object" ? payload.seo : {};
      payload.seo.title = _trimOrNull(getValue("edit_seo_title"));
      payload.seo.description = _trimOrNull(getValue("edit_seo_description"));

      payload.taxonomy = payload.taxonomy && typeof payload.taxonomy === "object" ? payload.taxonomy : {};
      const primaryText = String(getValue("edit_taxonomy_primary") || "").trim();
      if (primaryText) {
        payload.taxonomy.primary = primaryText
          .split(">")
          .map((t) => t.trim())
          .filter((t) => t);
      } else {
        payload.taxonomy.primary = null;
      }

      const imageUrls = _splitLines(getValue("edit_product_images"));
      const existingMedia = Array.isArray(payload.media) ? payload.media : [];
      const nonImageMedia = existingMedia.filter((item) => (item && item.type) !== "image");
      const imageMedia = imageUrls.map((url, index) => ({
        url,
        type: "image",
        alt: null,
        position: index + 1,
        is_primary: index === 0,
        variant_skus: [],
      }));
      payload.media = imageMedia.concat(nonImageMedia);
    };

    const applyVariantEdits = () => {
      const rows = editor.querySelectorAll("[data-variant-row]");
      const variants = Array.isArray(payload.variants) ? payload.variants : [];
      const updated = [];

      rows.forEach((row) => {
        const index = Number.parseInt(row.dataset.index || "0", 10);
        const base = variants[index] && typeof variants[index] === "object" ? variants[index] : {};
        const next = JSON.parse(JSON.stringify(base));

        const fieldVal = (name) => {
          const el = row.querySelector(`[data-field='${name}']`);
          if (!el) {
            return "";
          }
          if (el.type === "checkbox") {
            return el.checked;
          }
          return el.value;
        };

        next.sku = _trimOrNull(fieldVal("sku"));
        next.title = _trimOrNull(fieldVal("title"));

        const amount = _trimOrNull(fieldVal("price_amount"));
        const currency = _trimOrNull(fieldVal("price_currency"));
        if (amount || currency) {
          next.price = next.price && typeof next.price === "object" ? next.price : {};
          next.price.current = { amount: amount || null, currency: currency || null };
        } else {
          next.price = null;
        }

        const qtyText = _trimOrNull(fieldVal("inventory_qty"));
        const qty = qtyText !== null ? Number.parseInt(qtyText, 10) : null;
        const available = fieldVal("inventory_available");
        next.inventory = next.inventory && typeof next.inventory === "object" ? next.inventory : {};
        next.inventory.quantity = Number.isFinite(qty) ? Math.max(0, qty) : null;
        next.inventory.available = typeof available === "boolean" ? available : null;

        const weightValue = _trimOrNull(fieldVal("weight_value"));
        const weightUnit = _trimOrNull(fieldVal("weight_unit")) || "g";
        if (weightValue) {
          next.weight = { value: weightValue, unit: weightUnit };
        } else {
          next.weight = null;
        }

        const variantImageUrl = _trimOrNull(fieldVal("variant_image_url"));
        if (variantImageUrl) {
          next.media = [
            {
              url: variantImageUrl,
              type: "image",
              alt: null,
              position: 1,
              is_primary: true,
              variant_skus: next.sku ? [next.sku] : [],
            },
          ];
        } else {
          next.media = Array.isArray(next.media) ? next.media : [];
        }

        updated.push(next);
      });

      payload.variants = updated;
    };

    saveBtn.addEventListener("click", () => {
      try {
        applyBasicEdits();
        applyVariantEdits();
        exportB64Input.value = _encodeJsonB64(payload);
        payloadScript.textContent = JSON.stringify(payload);

        if (status) {
          status.textContent = `Saved. Export payload updated at ${new Date().toLocaleTimeString()}.`;
        }
      } catch (err) {
        if (status) {
          status.textContent = `Save failed: ${err}`;
        }
      }
    });
  };

  const _applyProductEditsFromCard = (card, product) => {
    const fieldVal = (name) => {
      const el = card.querySelector(`[data-field='${name}']`);
      if (!el) {
        return "";
      }
      if (el.type === "checkbox") {
        return el.checked;
      }
      return el.value;
    };

    product.title = _trimOrNull(fieldVal("title"));
    product.description = _trimOrNull(fieldVal("description"));
    product.vendor = _trimOrNull(fieldVal("vendor"));
    product.brand = _trimOrNull(fieldVal("brand"));
    product.tags = _splitCommaTokens(fieldVal("tags"));

    product.source = product.source && typeof product.source === "object" ? product.source : {};
    product.source.slug = _trimOrNull(fieldVal("source_slug"));
    product.source.url = _trimOrNull(fieldVal("source_url"));

    product.seo = product.seo && typeof product.seo === "object" ? product.seo : {};
    product.seo.title = _trimOrNull(fieldVal("seo_title"));
    product.seo.description = _trimOrNull(fieldVal("seo_description"));

    product.taxonomy = product.taxonomy && typeof product.taxonomy === "object" ? product.taxonomy : {};
    const primaryText = String(fieldVal("taxonomy_primary") || "").trim();
    if (primaryText) {
      product.taxonomy.primary = primaryText
        .split(">")
        .map((t) => t.trim())
        .filter((t) => t);
    } else {
      product.taxonomy.primary = null;
    }

    const imageUrls = _splitLines(fieldVal("product_images"));
    const existingMedia = Array.isArray(product.media) ? product.media : [];
    const nonImageMedia = existingMedia.filter((item) => (item && item.type) !== "image");
    const imageMedia = imageUrls.map((url, index) => ({
      url,
      type: "image",
      alt: null,
      position: index + 1,
      is_primary: index === 0,
      variant_skus: [],
    }));
    product.media = imageMedia.concat(nonImageMedia);

    const variantRows = card.querySelectorAll("[data-variant-row]");
    const variants = Array.isArray(product.variants) ? product.variants : [];
    const updated = [];

    variantRows.forEach((row) => {
      const vIndex = Number.parseInt(row.dataset.variantIndex || "0", 10);
      const base = variants[vIndex] && typeof variants[vIndex] === "object" ? variants[vIndex] : {};
      const next = JSON.parse(JSON.stringify(base));

      const vFieldVal = (name) => {
        const el = row.querySelector(`[data-field='${name}']`);
        if (!el) {
          return "";
        }
        if (el.type === "checkbox") {
          return el.checked;
        }
        return el.value;
      };

      next.sku = _trimOrNull(vFieldVal("sku"));
      next.title = _trimOrNull(vFieldVal("title"));

      const amount = _trimOrNull(vFieldVal("price_amount"));
      const currency = _trimOrNull(vFieldVal("price_currency"));
      if (amount || currency) {
        next.price = next.price && typeof next.price === "object" ? next.price : {};
        next.price.current = { amount: amount || null, currency: currency || null };
      } else {
        next.price = null;
      }

      const qtyText = _trimOrNull(vFieldVal("inventory_qty"));
      const qty = qtyText !== null ? Number.parseInt(qtyText, 10) : null;
      const available = vFieldVal("inventory_available");
      next.inventory = next.inventory && typeof next.inventory === "object" ? next.inventory : {};
      next.inventory.quantity = Number.isFinite(qty) ? Math.max(0, qty) : null;
      next.inventory.available = typeof available === "boolean" ? available : null;

      const weightValue = _trimOrNull(vFieldVal("weight_value"));
      const weightUnit = _trimOrNull(vFieldVal("weight_unit")) || "g";
      if (weightValue) {
        next.weight = { value: weightValue, unit: weightUnit };
      } else {
        next.weight = null;
      }

      const variantImageUrl = _trimOrNull(vFieldVal("variant_image_url"));
      if (variantImageUrl) {
        next.media = [
          {
            url: variantImageUrl,
            type: "image",
            alt: null,
            position: 1,
            is_primary: true,
            variant_skus: next.sku ? [next.sku] : [],
          },
        ];
      } else {
        next.media = Array.isArray(next.media) ? next.media : [];
      }

      updated.push(next);
    });

    product.variants = updated;
  };

  const initBatchProductEditor = () => {
    const batchEditor = document.querySelector("[data-product-editor-batch]");
    if (!batchEditor) {
      return;
    }

    const payloadScript = document.getElementById("editor-products-payload");
    if (!payloadScript) {
      return;
    }

    let payloads;
    try {
      payloads = JSON.parse(payloadScript.textContent || "[]");
    } catch {
      return;
    }
    if (!Array.isArray(payloads)) {
      return;
    }

    const saveBtn = batchEditor.querySelector("[data-action='save-batch-products']");
    const status = batchEditor.querySelector("[data-role='batch-save-status']");
    const exportB64Input = document.querySelector(
      "form[action='/export-from-product.csv'] input[name='product_json_b64']",
    );
    if (!saveBtn || !exportB64Input) {
      return;
    }

    saveBtn.addEventListener("click", () => {
      try {
        const cards = batchEditor.querySelectorAll("[data-batch-product]");
        cards.forEach((card) => {
          const index = Number.parseInt(card.dataset.productIndex || "0", 10);
          if (index < payloads.length) {
            _applyProductEditsFromCard(card, payloads[index]);
          }
        });

        exportB64Input.value = _encodeJsonB64(payloads);
        payloadScript.textContent = JSON.stringify(payloads);

        const summaries = batchEditor.querySelectorAll("[data-batch-product] .batch-product-title");
        summaries.forEach((el, i) => {
          if (i < payloads.length && payloads[i].title) {
            el.textContent = payloads[i].title;
          }
        });

        if (status) {
          status.textContent = `Saved ${payloads.length} product(s). Export payload updated at ${new Date().toLocaleTimeString()}.`;
        }
      } catch (err) {
        if (status) {
          status.textContent = `Save failed: ${err}`;
        }
      }
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    initUrlExportForm();
    initCsvImportForm();
    initCsvPreviewExportForm();
    initProductEditor();
    initBatchProductEditor();
  });
})();
