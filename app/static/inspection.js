async function fetchInspectionPayload() {
  const response = await fetch("/api/inspection/runtime");
  if (!response.ok) {
    throw new Error("Nao foi possivel carregar o payload de inspecao.");
  }
  return response.json();
}

function card(label, value) {
  return `
    <article class="summary-card">
      <div class="label">${label}</div>
      <div class="value">${value}</div>
    </article>
  `;
}

function tag(value) {
  const warning = ["high", "medium", "benchmark_regression_detected"].includes(String(value));
  return `<span class="tag${warning ? " warning" : ""}">${value || "-"}</span>`;
}

function renderSummaryCards(payload) {
  const summary = payload.benchmark_summary || {};
  const session = payload.session || {};
  document.getElementById("summary-cards").innerHTML = [
    card("Benchmark State", tag(summary.pedagogical_benchmark_state || "not_available")),
    card("Readiness", tag(summary.benchmark_readiness || "benchmark_insufficient")),
    card("Alignment", Number(summary.benchmark_alignment_score || 0).toFixed(2)),
    card("Regression Severity", tag(summary.benchmark_regression_severity || "none")),
    card("Total Cases", summary.benchmark_total_cases ?? 0),
    card("Session", session.session_id || "No session"),
  ].join("");
}

function renderKv(targetId, data) {
  const target = document.getElementById(targetId);
  const entries = Object.entries(data || {});
  if (!entries.length) {
    target.innerHTML = '<p class="empty">No runtime data available.</p>';
    return;
  }
  target.innerHTML = `<div class="kv-grid">${entries
    .map(
      ([key, value]) => `
        <div class="kv-row">
          <div class="kv-key">${key}</div>
          <div>${typeof value === "object" ? `<pre>${JSON.stringify(value, null, 2)}</pre>` : value}</div>
        </div>
      `
    )
    .join("")}</div>`;
}

function renderCaseReports(payload, filter = "") {
  const reports = (payload.benchmark_case_reports || []).filter((report) => {
    const haystack = `${report.case_id} ${report.case_name} ${report.case_category}`.toLowerCase();
    return haystack.includes(filter.toLowerCase());
  });
  const body = document.getElementById("case-report-body");
  if (!reports.length) {
    body.innerHTML = '<tr><td colspan="7" class="empty">No benchmark case reports available.</td></tr>';
    return;
  }
  body.innerHTML = reports
    .map(
      (report) => `
        <tr>
          <td>${report.case_id}<br /><small>${report.case_name}</small></td>
          <td>${report.case_category}</td>
          <td>${tag(report.benchmark_case_status)}</td>
          <td>${Number(report.expectation_alignment || 0).toFixed(2)}</td>
          <td>${(report.regression_flags || []).join(", ") || "-"}</td>
          <td>${Number(report.validation_confidence || 0).toFixed(2)}</td>
          <td>${report.case_benchmark_summary || "-"}</td>
        </tr>
      `
    )
    .join("");
}

function renderPayload(payload) {
  document.getElementById("status-banner").textContent = payload.inspection_available
    ? "Inspection payload loaded from the latest runtime session."
    : "No runtime data available yet. Start a session to inspect benchmark and validation metadata.";

  renderSummaryCards(payload);
  renderCaseReports(payload);
  renderKv("scientific-validation", payload.scientific_runtime_validation);
  renderKv("stability-metrics", payload.stability_metrics);
  renderKv("comparative-analytics", payload.comparative_session_analytics);
  renderKv("dataset-awareness", payload.validation_dataset_awareness);
  renderKv("session-export-debug", payload.session_export_debug);
  renderKv("controlled-tuning-registry", payload.controlled_tuning_registry);
  renderKv("tuning-profile-comparison", payload.tuning_profile_benchmark_comparison);
  renderKv("manual-experiment-inspection", payload.manual_experiment_inspection);
  renderKv("longitudinal-retention", payload.longitudinal_retention);
  document.getElementById("raw-json").textContent = JSON.stringify(payload, null, 2);
}

async function loadInspection() {
  try {
    const payload = await fetchInspectionPayload();
    window.__inspectionPayload = payload;
    renderPayload(payload);
  } catch (error) {
    document.getElementById("status-banner").textContent = error.message;
  }
}

document.getElementById("refresh-button").addEventListener("click", loadInspection);
document.getElementById("case-filter").addEventListener("input", (event) => {
  renderCaseReports(window.__inspectionPayload || {}, event.target.value || "");
});

loadInspection();
