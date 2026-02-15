(() => {
  const config = window.ECT || {};
  const weightUnitAllowlist = config.weightUnitAllowlist || {};
  const weightUnitDefaults = config.weightUnitDefaults || {};
  const sourceWeightRequiredPlatforms = new Set(config.sourceWeightRequiredPlatforms || []);

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

  document.addEventListener("DOMContentLoaded", () => {
    initUrlExportForm();
    initCsvImportForm();
    initCsvPreviewExportForm();
  });
})();

