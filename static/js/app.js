let scoreChart = null;

// Load product autocomplete on page load
document.addEventListener("DOMContentLoaded", async () => {
  try {
    const res = await fetch("http://127.0.0.1:5000/api/products");
    const data = await res.json();
    const dl   = document.getElementById("productSuggestions");
    const pills = document.getElementById("examplePills");
    const examples = data.products.slice(0, 8);

    data.products.forEach(p => {
      const opt = document.createElement("option"); opt.value = p; dl.appendChild(opt);
    });

    examples.forEach(p => {
      const btn = document.createElement("button");
      btn.className = "btn btn-outline-secondary btn-sm rounded-pill";
      btn.textContent = p;
      btn.onclick = () => {
        document.getElementById("productInput").value = p;
        getRecommendations();
      };
      pills.appendChild(btn);
    });
  } catch(e) { console.warn("Could not load products", e); }

  document.getElementById("productInput").addEventListener("keydown", e => {
    if (e.key === "Enter") getRecommendations();
  });
});

async function getRecommendations() {
  const product = document.getElementById("productInput").value.trim();
  const errEl   = document.getElementById("inputError");

  errEl.classList.add("d-none");
  if (!product) {
    errEl.textContent = "Please enter a product name.";
    errEl.classList.remove("d-none");
    return;
  }

  document.getElementById("resultsSection").style.display = "";
  document.getElementById("loadingState").classList.remove("d-none");
  document.getElementById("resultsHeader").classList.add("d-none");

  try {
    const res = await fetch("http://127.0.0.1:5000/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product })
});
    const data = await res.json();

    document.getElementById("loadingState").classList.add("d-none");
    document.getElementById("resultsHeader").classList.remove("d-none");

    if (!data.success) {
      errEl.textContent = data.error || "Something went wrong.";
      errEl.classList.remove("d-none");
      document.getElementById("resultsSection").style.display = "none";
      return;
    }

    renderResults(data);
  } catch(e) {
    document.getElementById("loadingState").classList.add("d-none");
    errEl.textContent = "Network error — make sure Flask is running.";
    errEl.classList.remove("d-none");
  }
}

function renderResults(data) {
  const recs = data.recommendations;

  document.getElementById("resultProduct").textContent = data.product;
  document.getElementById("modelInfo").textContent =
    `${data.model_info.cost_model} (cost) · ${data.model_info.co2_model} (CO₂)`;
  document.getElementById("queryBadge").textContent = `Query #${data.query_id}`;

  // Metrics row
  const top = recs[0];
  document.getElementById("metricsRow").innerHTML = `
    <div class="col-6 col-md-3">
      <div class="card border-0 shadow-sm text-center py-3">
        <div class="fw-bold fs-3 text-success">${top.eco_score}</div>
        <div class="text-muted small">Top Eco Score</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="card border-0 shadow-sm text-center py-3">
        <div class="fw-bold fs-3 text-success">${top.biodegradability}%</div>
        <div class="text-muted small">Biodegradability</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="card border-0 shadow-sm text-center py-3">
        <div class="fw-bold fs-3 text-danger">${top.co2_efficiency}%</div>
        <div class="text-muted small">CO₂ Efficiency</div>
      </div>
    </div>
    <div class="col-6 col-md-3">
      <div class="card border-0 shadow-sm text-center py-3">
        <div class="fw-bold fs-3">$${top.cost_predicted}</div>
        <div class="text-muted small">Est. Cost (USD)</div>
      </div>
    </div>`;

  // Recommendation cards
  const medals = ["🥇", "🥈", "🥉"];
  const gradeClass = g => g === "Excellent" ? "grade-excellent" : g === "Good" ? "grade-good" : "grade-fair";
  const ecoPill = g => g === "Excellent" ? "eco-excellent" : g === "Good" ? "eco-good" : "eco-fair";

  document.getElementById("recCards").innerHTML = recs.map((r, i) => `
    <div class="col-md-4">
      <div class="card rec-card shadow-sm h-100 ${i === 0 ? "rank-1" : ""}">
        <div class="card-body p-4">
          ${i === 0 ? '<div class="best-badge badge bg-success mb-2">Top Recommendation</div><br>' : ''}
          <div class="d-flex align-items-start gap-3 mb-3">
            <span class="medal">${medals[i]}</span>
            <div class="flex-grow-1">
              <h6 class="fw-bold mb-0">${r.material_name}</h6>
              <small class="text-muted">${r.rank === 1 ? data.product + " · " : ""}Material type info</small>
            </div>
            <div class="eco-score-circle ${gradeClass(r.grade)}">
              <span class="score-num">${r.eco_score}</span>
              <span>/100</span>
            </div>
          </div>
          <div class="metric-bar-wrap">
            <label><span>Biodegradability</span><span>${r.biodegradability}%</span></label>
            <div class="metric-bar"><div class="metric-bar-fill fill-biodeg" style="width:${r.biodegradability}%"></div></div>
          </div>
          <div class="metric-bar-wrap">
            <label><span>CO₂ Efficiency</span><span>${r.co2_efficiency}%</span></label>
            <div class="metric-bar"><div class="metric-bar-fill fill-co2" style="width:${r.co2_efficiency}%"></div></div>
          </div>
          <div class="metric-bar-wrap">
            <label><span>Recyclability</span><span>${r.recyclability}%</span></label>
            <div class="metric-bar"><div class="metric-bar-fill fill-recycle" style="width:${r.recyclability}%"></div></div>
          </div>
          <hr class="my-3">
          <div class="d-flex justify-content-between align-items-center">
            <span class="eco-pill ${ecoPill(r.grade)}">${r.grade}</span>
            <span class="fw-semibold">$${r.cost_predicted} <small class="text-muted fw-normal">est.</small></span>
          </div>
        </div>
      </div>
    </div>`).join("");

  // Comparison table
  document.getElementById("comparisonBody").innerHTML = recs.map((r, i) => `
    <tr>
      <td>${medals[i]} #${r.rank}</td>
      <td class="fw-semibold">${r.material_name}</td>
      <td><span class="badge bg-secondary">${r.material_type || "—"}</span></td>
      <td>${r.biodegradability}%</td>
      <td>${r.co2_efficiency}%</td>
      <td>${r.recyclability}%</td>
      <td><span class="eco-pill ${ecoPill(r.grade)}">${r.eco_score}</span></td>
      <td>$${r.cost_predicted}</td>
    </tr>`).join("");

  // Bar chart
  if (scoreChart) scoreChart.destroy();
  const ctx = document.getElementById("scoreChart").getContext("2d");
  scoreChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: recs.map(r => r.material_name),
      datasets: [
        { label: "Biodegradability", data: recs.map(r => r.biodegradability), backgroundColor: "#27ae60cc" },
        { label: "CO₂ Efficiency",   data: recs.map(r => r.co2_efficiency),   backgroundColor: "#e74c3ccc" },
        { label: "Recyclability",    data: recs.map(r => r.recyclability),     backgroundColor: "#2980b9cc" },
      ]
    },
    options: {
      responsive: true,
      plugins: { legend: { position: "top" } },
      scales: {
        y: { min: 0, max: 100, title: { display: true, text: "Score (%)" } }
      }
    }
  });
}
