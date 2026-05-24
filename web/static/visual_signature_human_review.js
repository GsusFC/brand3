(function () {
  function byName(form, name) {
    var field = form.elements[name];
    if (!field) {
      return "";
    }
    return String(field.value || "").trim();
  }

  function collectEvidenceRefs(form) {
    return Array.prototype.slice
      .call(form.querySelectorAll('input[name="evidence_ref"]'))
      .map(function (input) {
        return input.value;
      })
      .filter(Boolean);
  }

  function collectAnswers() {
    return Array.prototype.slice
      .call(document.querySelectorAll(".human-review-question"))
      .map(function (node) {
        var checked = node.querySelector('input[type="radio"]:checked');
        return {
          question_id: node.dataset.questionId || "",
          question: node.dataset.questionText || "",
          question_category: node.dataset.questionCategory || "",
          observation_type: node.dataset.observationType || "",
          answer_type: node.dataset.answerType || "",
          answer: checked ? checked.value : "unanswered"
        };
      });
  }

  function draftFilename(payload) {
    var brand = String(payload.brand || "visual-signature")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
    var stamp = payload.reviewed_at.replace(/[^0-9]/g, "").slice(0, 14);
    return brand + "-draft-review-" + stamp + ".json";
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
    return {
      schema_version: "visual-signature-draft-review-1",
      record_type: "human_review_draft",
      draft_status: "draft_only",
      official_review_record: false,
      ingestion_status: "not_ingested",
      brand: form.dataset.brandName || "",
      capture_id: form.dataset.captureId || "",
      queue_id: form.dataset.queueId || "",
      reviewer_id: byName(form, "reviewer_id"),
      reviewed_at: new Date().toISOString(),
      review_outcome: byName(form, "review_outcome"),
      confidence_bucket: byName(form, "confidence_bucket"),
      answers: collectAnswers(),
      notes: byName(form, "notes"),
      contradiction_notes: byName(form, "contradictions"),
      unresolved_notes: byName(form, "missing_evidence"),
      evidence_refs: collectEvidenceRefs(form),
      warnings: [
        "This is not an official review record.",
        "Exported drafts must be validated before ingestion.",
        "Do not auto-ingest draft reviews."
      ]
    };
  }

  function attachExport(form) {
    var button = form.querySelector("[data-export-draft-review]");
    var status = form.querySelector("[data-draft-export-status]");
    if (!button) {
      return;
    }
    button.addEventListener("click", function () {
      var payload = buildDraft(form);
      downloadJson(payload);
      if (status) {
        status.textContent = "Draft JSON exported locally. Official review records are untouched.";
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    Array.prototype.slice
      .call(document.querySelectorAll("[data-human-review-draft-form]"))
      .forEach(attachExport);
  });
})();
