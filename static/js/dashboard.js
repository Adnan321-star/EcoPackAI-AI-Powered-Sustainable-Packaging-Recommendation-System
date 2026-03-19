let charts = {};

document.addEventListener("DOMContentLoaded", loadDashboard);

async function loadDashboard() {
  try {
    const [dash, history] = await Promise.all([
      fetch("http://127.0.0.1:5000/api/dashboard").then(r => r.json()),
      fetch("http://127.0.0.1:5000/api/history?limit=8").then(r => r.json())
    ]);
    renderKPIs(dash);
    renderTrendChart(dash.daily_trend);
    renderEcoDist(dash.eco_score_dist);
    renderTopMats(dash.top_materials);
    renderRecentTable(history.history);
  } catch(e) {
    console.error("Dashboard load failed:", e);
  }
}

function renderKPIs(d) {
  document.getElementById("kpiTotal").textContent = d.total_queries.toLocaleString();
  document.getElementById("kpiCO2").textContent =
    (d.co2_reduction_pct >= 0 ? "↓ " : "↑ ") + Math.abs(d.co2_reduction_pct) + "%";
  document.getElementById("kpiCost").textContent =
    (d.cost_savings_pct >= 0 ? "↓ " : "↑ ") + Math.abs(d.cost_savings_pct) + "%";
  document.getElementById("kpiEco").textContent = d.avg_eco_score + " / 100";
}

function renderTrendChart(data) {
  if (charts.trend) charts.trend.destroy();
  const ctx = document.getElementById("trendChart").getContext("2d");
  charts.trend = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.map(d => d.day),
      datasets: [{
        label: "Queries",
        data: data.map(d => d.count),
        borderColor: "#27ae60",
        backgroundColor: "#27ae6022",
        tension: 0.4,
        fill: true,
        pointRadius: 4,
        pointBackgroundColor: "#27ae60"
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 } }
      }
    }
  });
}

function renderEcoDist(data) {
  if (charts.ecoDist) charts.ecoDist.destroy();
  const ctx = document.getElementById("ecoDistChart").getContext("2d");
  charts.ecoDist = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: data.map(d => d.label),
      datasets: [{
        data: data.map(d => d.count),
        backgroundColor: ["#c0392b", "#d4ac0d", "#2980b9", "#27ae60"],
        borderWidth: 2,
        borderColor: "#fff"
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } }
      },
      cutout: "60%"
    }
  });
}

function renderTopMats(data) {
  if (charts.topMats) charts.topMats.destroy();
  const ctx = document.getElementById("topMatsChart").getContext("2d");
  charts.topMats = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map(d => d.material_name),
      datasets: [{
        label: "Times Recommended (#1)",
        data: data.map(d => d.count),
        backgroundColor: ["#27ae60cc","#2980b9cc","#8e44adcc","#e67e22cc","#e74c3ccc"],
        borderRadius: 6
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, ticks: { precision: 0 } } }
    }
  });
}

function renderRecentTable(history) {
  const gradeClass = s => s >= 70 ? "eco-excellent" : s >= 50 ? "eco-good" : "eco-fair";
  document.getElementById("recentTable").innerHTML = history.map(h => `
    <tr>
      <td class="fw-semibold">${h.product_name}</td>
      <td>${h.top_material || "—"}</td>
      <td><span class="eco-pill ${gradeClass(h.top_eco_score)}">${h.top_eco_score}</span></td>
      <td class="text-muted small">${new Date(h.queried_at).toLocaleString()}</td>
    </tr>`).join("") || '<tr><td colspan="4" class="text-center text-muted py-4">No data yet</td></tr>';
}