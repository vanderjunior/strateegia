async function fetchDashboardOverview() {
  const response = await fetch("/api/dashboard/overview", {
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Unable to load dashboard." }));
    throw new Error(payload.detail || "Unable to load dashboard.");
  }

  return response.json();
}

function badgeClass(severity) {
  return {
    blocked: "badge-blocked",
    error: "badge-error",
    warning: "badge-warning",
    info: "badge-info",
  }[severity || "info"];
}

function renderStackItem(title, body, badgeLabel = "", badgeSeverity = "info") {
  const badge = badgeLabel
    ? `<span class="badge ${badgeClass(badgeSeverity)}">${badgeLabel}</span>`
    : "";
  return `
    <article class="stack-item">
      <div class="stack-title-row">
        <strong>${title}</strong>
        ${badge}
      </div>
      <p>${body}</p>
    </article>
  `;
}

function renderStatusCards(overview) {
  const cards = [
    ["Materials", `${overview.materials.total_materials} total · ${overview.materials.processed_count} processed · ${overview.materials.ocr_required_count} OCR-required`],
    ["Document Pipeline", `${overview.document_pipeline.total_documents} docs · ${overview.document_pipeline.metadata_ready_count} metadata-ready · ${overview.document_pipeline.extraction_pending_count} pending`],
    ["Edital", overview.edital.edital_available ? `${overview.edital.topics_detected} topics · ${overview.edital.bibliography_items_detected} bibliography items` : "Not available yet"],
    ["Coverage / Alignment", overview.alignment.alignment_available ? `${overview.alignment.topics_with_coverage} topics with coverage · ${overview.alignment.gaps_detected} gaps` : "Not available yet"],
    ["Curriculum Graph", overview.curriculum_graph.graph_available ? `${overview.curriculum_graph.subject_count} subjects · ${overview.curriculum_graph.topic_count} topics` : "Not available yet"],
    ["Study Cycle", overview.study_cycle.cycle_available ? `${overview.study_cycle.topic_slot_count} topic slots · ${overview.study_cycle.review_slot_count} review slots` : "Not available yet"],
    ["Exam Profile", overview.exam_profile.profile_available ? `${overview.exam_profile.format_type} · confidence ${overview.exam_profile.heuristic_confidence}` : "Not available yet"],
    ["Simulado Blueprint", overview.simulado_blueprint.blueprint_available ? `${overview.simulado_blueprint.question_slot_count} slots · ${overview.simulado_blueprint.readiness_state}` : "Not available yet"],
  ];

  document.getElementById("status-cards").innerHTML = cards
    .map(([title, body]) => `<article class="status-card"><h3>${title}</h3><p>${body}</p></article>`)
    .join("");
}

function renderOverview(overview) {
  document.getElementById("dashboard-summary").textContent = overview.dashboard_summary || "No summary available.";
  document.getElementById("user-label").textContent = overview.user.display_name || overview.user.username || "authenticated user";

  const nextStep = overview.primary_next_step;
  document.getElementById("primary-next-step").innerHTML = nextStep
    ? renderStackItem(nextStep.title, nextStep.description, nextStep.severity, nextStep.severity)
    : `<div class="empty-state">No pending action right now.</div>`;

  const continuation = overview.continuation.continuation_available
    ? renderStackItem(
        overview.continuation.recommended_resume_label || "Resume available",
        `Last topic: ${overview.continuation.last_topic_id || "-"}`
      )
    : `<div class="empty-state">Not enough data yet.</div>`;
  document.getElementById("continuation-summary").innerHTML = continuation;

  renderStatusCards(overview);

  document.getElementById("pending-actions").innerHTML = overview.pending_actions.length
    ? overview.pending_actions
        .map((item) => renderStackItem(item.title, item.description, item.severity, item.severity))
        .join("")
    : `<div class="empty-state">No pending actions.</div>`;

  document.getElementById("warnings-list").innerHTML = overview.warnings.length
    ? overview.warnings
        .map((item) => renderStackItem(item.code, item.message, item.severity, item.severity))
        .join("")
    : `<div class="empty-state">No warnings.</div>`;

  document.getElementById("recent-materials").innerHTML = overview.materials.recent_materials.length
    ? overview.materials.recent_materials
        .map((item) => renderStackItem(item.display_filename, `${item.content_type || "unknown"} · ${item.status || "uploaded"}`))
        .join("")
    : `<div class="empty-state">No materials uploaded yet.</div>`;

  document.getElementById("pipeline-states").innerHTML = overview.document_pipeline.latest_pipeline_states.length
    ? overview.document_pipeline.latest_pipeline_states
        .map((item) => renderStackItem(item.display_filename, `${item.current_stage || "uploaded"} · ${item.extraction_status || "pending"}`))
        .join("")
    : `<div class="empty-state">No pipeline states yet.</div>`;

  document.getElementById("progress-summary").innerHTML = overview.progress.progress_available
    ? [
        renderStackItem("Attempts", `${overview.progress.total_attempts} total · accuracy ${overview.progress.accuracy}`),
        renderStackItem("Topics", `${overview.progress.studied_topics_count} studied · ${overview.progress.weak_topics_count} weak`),
      ].join("")
    : `<div class="empty-state">Not enough data yet.</div>`;

  document.getElementById("retention-summary").innerHTML = overview.retention.retention_available
    ? renderStackItem(
        overview.retention.aggregate_retention_state,
        `Durable ${overview.retention.durable_microtopics_count} · Fragile ${overview.retention.fragile_microtopics_count}`
      )
    : `<div class="empty-state">Not enough data yet.</div>`;

  document.getElementById("raw-json").textContent = JSON.stringify(overview, null, 2);
}

async function startDashboard() {
  try {
    const overview = await fetchDashboardOverview();
    renderOverview(overview);
  } catch (error) {
    document.getElementById("dashboard-summary").textContent = error.message;
    document.getElementById("primary-next-step").innerHTML = `<div class="empty-state">Dashboard could not be loaded.</div>`;
  }
}

startDashboard();
