(function () {
  function checkedValue(name) {
    var field = document.querySelector('input[name="' + name + '"]:checked');
    return field ? String(field.value || "").trim() : "";
  }

  function checkedValues(name) {
    return Array.prototype.slice
      .call(document.querySelectorAll('input[name="' + name + '"]:checked'))
      .map(function (field) {
        return String(field.value || "").trim();
      })
      .filter(Boolean);
  }

  function textValue(name) {
    var field = document.querySelector('[name="' + name + '"]');
    return field ? String(field.value || "").trim() : "";
  }

  function parseJson(value) {
    try {
      return JSON.parse(value || "{}");
    } catch (_error) {
      return {};
    }
  }

  function collectDimensionReviews(root) {
    return Array.prototype.slice.call(root.querySelectorAll("[data-dimension-review]")).map(function (card) {
      var dimensionId = card.dataset.dimensionId || "";
      return {
        dimension_id: dimensionId,
        dimension_name: card.dataset.dimensionName || "",
        candidate_available: card.dataset.candidateAvailable === "true",
        requires_human_review: card.dataset.requiresHumanReview === "true",
        reviewer_decision: checkedValue("decision_" + dimensionId) || "unreviewed",
        reason_tags: checkedValues("reason_" + dimensionId),
        reviewer_notes: textValue("notes_" + dimensionId)
      };
    });
  }

  function draftFilename(payload) {
    var stamp = payload.created_at.replace(/[^0-9]/g, "").slice(0, 14);
    return "brand3-lab-state-first-review-draft-" + payload.case_id + "-" + stamp + ".json";
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

  function buildDraft(root) {
    var createdAt = new Date().toISOString();
    return {
      review_schema_version: root.dataset.reviewSchemaVersion || "brand3-lab-state-first-review-draft-1",
      record_type: "brand3_lab_state_first_review_draft",
      draft_only: true,
      not_persisted: true,
      official_record: false,
      scoring_impact: false,
      report_mutation: false,
      created_at: createdAt,
      run_id: root.dataset.runId || "",
      case_id: root.dataset.caseId || "",
      brand: root.dataset.caseBrand || "",
      source_artifacts: parseJson(root.dataset.sourceArtifacts),
      dimension_reviews: collectDimensionReviews(root),
      overall_decision: checkedValue("overall_decision") || "unreviewed",
      reviewer_notes: {
        overall: textValue("overall_notes")
      },
      warnings: [
        "Draft-only Brand3 Lab review.",
        "No review is persisted from this route.",
        "Reviewer decisions do not affect scoring.",
        "Lab candidates are not official Brand Audit findings."
      ]
    };
  }

  function attach(root) {
    var button = document.querySelector("[data-export-lab-review-draft]");
    var status = document.querySelector("[data-lab-review-export-status]");
    if (!button) {
      return;
    }
    button.addEventListener("click", function () {
      var payload = buildDraft(root);
      downloadJson(payload);
      if (status) {
        status.textContent = "Draft JSON exported locally. No record was persisted.";
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.querySelector("[data-lab-review-form]");
    if (root) {
      attach(root);
    }
  });
})();
