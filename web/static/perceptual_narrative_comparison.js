(function () {
  function visiblePairs() {
    return Array.prototype.slice.call(document.querySelectorAll("[data-comparison-pair]"));
  }

  function byName(form, name) {
    var field = form.elements[name];
    if (!field) {
      return "";
    }
    if (field instanceof RadioNodeList) {
      return String(field.value || "").trim();
    }
    return String(field.value || "").trim();
  }

  function selectedPairIds() {
    var selector = document.querySelector("[data-comparison-brand-selector]");
    if (!selector || selector.value === "all") {
      return null;
    }
    return [selector.value];
  }

  function applyBrandFilter() {
    var ids = selectedPairIds();
    visiblePairs().forEach(function (card) {
      var visible = !ids || ids.indexOf(card.dataset.brandId || "") !== -1;
      card.hidden = !visible;
    });
  }

  function collectReviews(form) {
    return visiblePairs().map(function (card) {
      var brandId = card.dataset.brandId || "";
      return {
        brand: card.dataset.brandName || "",
        brand_id: brandId,
        reviewer_decision: byName(form, "decision_" + brandId) || "unreviewed",
        notes: byName(form, "notes_" + brandId)
      };
    });
  }

  function sourceMetadata(form) {
    var raw = form.dataset.sourceMetadata || "{}";
    try {
      return JSON.parse(raw);
    } catch (_error) {
      return {};
    }
  }

  function draftFilename(payload) {
    var stamp = payload.reviewed_at.replace(/[^0-9]/g, "").slice(0, 14);
    if (payload.case_id) {
      return "brand3-lab-case-comparison-draft-" + payload.case_id + "-" + stamp + ".json";
    }
    return "perceptual-narrative-comparison-draft-" + stamp + ".json";
  }

  function downloadJson(payload) {
    var blob = new Blob([JSON.stringify(payload, null, 2) + "\n"], {
      type: "application/json"
    });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = draftFilename(payload);
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function buildDraft(form) {
    var caseId = form.dataset.caseId || "";
    var caseBrand = form.dataset.caseBrand || "";
    if (caseId) {
      return {
        schema_version: "brand3-lab-case-comparison-draft-1",
        record_type: "brand3_lab_case_comparison_review_draft",
        draft_status: "draft_only",
        draft_only: true,
        not_persisted: true,
        official_record: false,
        persistence_status: "not_persisted",
        reviewed_at: new Date().toISOString(),
        case_id: caseId,
        brand: caseBrand,
        reviewer_decision: byName(form, "decision_" + caseId) || "unreviewed",
        notes: byName(form, "notes_" + caseId),
        comparison_source_metadata: sourceMetadata(form),
        warnings: [
          "Experimental Brand3 Lab case draft only.",
          "No review is persisted from this route.",
          "Do not ingest as an official record without validation."
        ]
      };
    }
    return {
      schema_version: "brand3-perceptual-narrative-comparison-draft-1",
      record_type: "perceptual_narrative_comparison_review_draft",
      draft_status: "draft_only",
      draft_only: true,
      not_persisted: true,
      official_record: false,
      persistence_status: "not_persisted",
      reviewed_at: new Date().toISOString(),
      selected_scope: selectedPairIds() || "all",
      reviews: collectReviews(form),
      warnings: [
        "Experimental lab draft only.",
        "No review is persisted from this route.",
        "Do not ingest as an official record without validation."
      ]
    };
  }

  function attachExport(form) {
    var button = form.querySelector("[data-export-comparison-draft]");
    var status = form.querySelector("[data-comparison-export-status]");
    if (!button) {
      return;
    }
    button.addEventListener("click", function () {
      var payload = buildDraft(form);
      downloadJson(payload);
      if (status) {
        status.textContent = "Draft JSON exported locally. No record was persisted.";
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var selector = document.querySelector("[data-comparison-brand-selector]");
    if (selector) {
      selector.addEventListener("change", applyBrandFilter);
    }
    Array.prototype.slice
      .call(document.querySelectorAll("[data-perceptual-comparison-form]"))
      .forEach(attachExport);
  });
})();
