let aliveChart = null;
let deadChart = null;
let energyChart = null;
let simTimer = null;
let replayTimer = null;
let currentSimState = null;
let simHistory = [];
let hoveredNode = null;
let lastCanvasGeometry = null;
let miniAliveChart = null;
let miniEnergyChart = null;

function byId(id) {
  return document.getElementById(id);
}

async function postJSON(url, payload = {}) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    let msg = `Request failed: ${res.status}`;
    try {
      const data = await res.json();
      if (data.error) msg = data.error;
    } catch (_) {}
    throw new Error(msg);
  }

  return await res.json();
}

function revealOnScroll() {
  const items = document.querySelectorAll(".reveal");
  if (!items.length) return;

  const obs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) entry.target.classList.add("visible");
    });
  }, { threshold: 0.12 });

  items.forEach(el => obs.observe(el));
}

function animateCounters() {
  const counters = document.querySelectorAll(".counter");
  if (!counters.length) return;

  const obs = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;

      const el = entry.target;
      const target = Number(el.dataset.target || 0);
      const duration = 1200;
      const startTime = performance.now();

      function update(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(target * eased).toLocaleString();
        if (progress < 1) requestAnimationFrame(update);
      }

      requestAnimationFrame(update);
      obs.unobserve(el);
    });
  }, { threshold: 0.4 });

  counters.forEach(counter => obs.observe(counter));
}

function buildCompareChart(canvasId, labelA, labelB, colorA, colorB) {
  const el = byId(canvasId);
  if (!el) return null;

  return new Chart(el.getContext("2d"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: labelA,
          data: [],
          borderColor: colorA,
          backgroundColor: colorA,
          borderWidth: 3,
          pointRadius: 0,
          tension: 0.28
        },
        {
          label: labelB,
          data: [],
          borderColor: colorB,
          backgroundColor: colorB,
          borderWidth: 3,
          pointRadius: 0,
          tension: 0.28
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 900, easing: "easeOutQuart" },
      plugins: {
        legend: { labels: { color: "#f5f7ff" } }
      },
      scales: {
        x: {
          ticks: { color: "#a9b2d0" },
          grid: { color: "rgba(255,255,255,0.06)" }
        },
        y: {
          beginAtZero: true,
          ticks: { color: "#a9b2d0" },
          grid: { color: "rgba(255,255,255,0.06)" }
        }
      }
    }
  });
}

function buildMiniChart(canvasId, label, color) {
  const el = byId(canvasId);
  if (!el) return null;

  return new Chart(el.getContext("2d"), {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        label,
        data: [],
        borderColor: color,
        backgroundColor: color,
        borderWidth: 2.5,
        pointRadius: 0,
        tension: 0.28
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#f5f7ff" } }
      },
      scales: {
        x: {
          ticks: { color: "#a9b2d0", maxTicksLimit: 6 },
          grid: { color: "rgba(255,255,255,0.05)" }
        },
        y: {
          beginAtZero: true,
          ticks: { color: "#a9b2d0", maxTicksLimit: 5 },
          grid: { color: "rgba(255,255,255,0.05)" }
        }
      }
    }
  });
}

/* -------- analysis -------- */

function setWinnerHero(winner) {
  const title = byId("winnerTitle");
  const text = byId("winnerText");
  const badge = byId("winnerBadge");
  if (!title || !text || !badge) return;

  badge.className = "winner-badge";
  if (winner === "LEACH") {
    title.textContent = "LEACH leads this comparison";
    text.textContent = "LEACH performed better for the selected seed based on death timing, lifetime, and final energy.";
    badge.textContent = "LEACH";
    badge.classList.add("leach");
  } else if (winner === "ZCR") {
    title.textContent = "ZCR leads this comparison";
    text.textContent = "ZCR performed better for the selected seed by balancing energy and delaying network failure.";
    badge.textContent = "ZCR";
    badge.classList.add("zcr");
  } else {
    title.textContent = "The protocols are tied";
    text.textContent = "Both protocols performed similarly for this seed.";
    badge.textContent = "TIE";
    badge.classList.add("tie");
  }
}

function updateMetricCards(leach, zcr) {
  const fndWinner =
    (leach.summary.first_dead_round || 0) > (zcr.summary.first_dead_round || 0) ? "LEACH" :
    (zcr.summary.first_dead_round || 0) > (leach.summary.first_dead_round || 0) ? "ZCR" : "TIE";

  const hndWinner =
    (leach.summary.half_dead_round || 0) > (zcr.summary.half_dead_round || 0) ? "LEACH" :
    (zcr.summary.half_dead_round || 0) > (leach.summary.half_dead_round || 0) ? "ZCR" : "TIE";

  const lifeWinner =
    leach.summary.rounds_completed > zcr.summary.rounds_completed ? "LEACH" :
    zcr.summary.rounds_completed > leach.summary.rounds_completed ? "ZCR" : "TIE";

  const energyWinner =
    leach.summary.total_energy_now > zcr.summary.total_energy_now ? "LEACH" :
    zcr.summary.total_energy_now > leach.summary.total_energy_now ? "ZCR" : "TIE";

  byId("cmpFndWinner").textContent = fndWinner;
  byId("cmpFndText").textContent = `LEACH: ${leach.summary.first_dead_round ?? "-"} | ZCR: ${zcr.summary.first_dead_round ?? "-"}`;

  byId("cmpHndWinner").textContent = hndWinner;
  byId("cmpHndText").textContent = `LEACH: ${leach.summary.half_dead_round ?? "-"} | ZCR: ${zcr.summary.half_dead_round ?? "-"}`;

  byId("cmpLifetimeWinner").textContent = lifeWinner;
  byId("cmpLifetimeText").textContent = `LEACH: ${leach.summary.rounds_completed} | ZCR: ${zcr.summary.rounds_completed}`;

  byId("cmpEnergyWinner").textContent = energyWinner;
  byId("cmpEnergyText").textContent = `LEACH: ${leach.summary.total_energy_now.toFixed(4)} J | ZCR: ${zcr.summary.total_energy_now.toFixed(4)} J`;
}

function updateProtocolTile(id, data) {
  const el = byId(id);
  if (!el) return;

  el.innerHTML = `
    <div class="tile-row"><span>Rounds</span><strong>${data.summary.rounds_completed}</strong></div>
    <div class="tile-row"><span>First Dead</span><strong>${data.summary.first_dead_round ?? "-"}</strong></div>
    <div class="tile-row"><span>Half Dead</span><strong>${data.summary.half_dead_round ?? "-"}</strong></div>
    <div class="tile-row"><span>Last Dead</span><strong>${data.summary.last_dead_round ?? "-"}</strong></div>
    <div class="tile-row"><span>Final Energy</span><strong>${data.summary.total_energy_now.toFixed(4)} J</strong></div>
  `;
}

function renderSummary(leach, zcr, winner) {
  const panel = byId("summaryPanel");
  if (!panel) return;

  panel.innerHTML = `
    <p><strong>Winner:</strong> <span class="winner-pill">${winner}</span></p>
    <p><strong>LEACH</strong> — First dead round: ${leach.summary.first_dead_round ?? "Not reached"}, Half dead round: ${leach.summary.half_dead_round ?? "Not reached"}, Last dead round: ${leach.summary.last_dead_round ?? "Not reached"}, Final energy: ${leach.summary.total_energy_now.toFixed(4)} J, Total rounds: ${leach.summary.rounds_completed}</p>
    <p><strong>ZCR</strong> — First dead round: ${zcr.summary.first_dead_round ?? "Not reached"}, Half dead round: ${zcr.summary.half_dead_round ?? "Not reached"}, Last dead round: ${zcr.summary.last_dead_round ?? "Not reached"}, Final energy: ${zcr.summary.total_energy_now.toFixed(4)} J, Total rounds: ${zcr.summary.rounds_completed}</p>
    <p>This run used the same seed for both protocols, so the comparison is fair.</p>
  `;
}

function bindAnalysisPage() {
  const runBtn = byId("runCompareBtn");
  if (!runBtn) return;

  aliveChart = buildCompareChart("aliveChart", "LEACH", "ZCR", "#6ea8ff", "#22c55e");
  deadChart = buildCompareChart("deadChart", "LEACH", "ZCR", "#60a5fa", "#4ade80");
  energyChart = buildCompareChart("energyChart", "LEACH", "ZCR", "#8b5cf6", "#22d3ee");

  runBtn.addEventListener("click", async () => {
    runBtn.disabled = true;
    runBtn.textContent = "Running...";

    try {
      const seed = Number(byId("compareSeedInput").value || 42);
      const data = await postJSON("/api/compare", { seed });

      const leach = data.leach;
      const zcr = data.zcr;

      const aliveLen = Math.max(leach.alive_history.length, zcr.alive_history.length);
      aliveChart.data.labels = Array.from({ length: aliveLen }, (_, i) => i + 1);
      aliveChart.data.datasets[0].data = leach.alive_history;
      aliveChart.data.datasets[1].data = zcr.alive_history;
      aliveChart.update();

      const deadLen = Math.max(leach.dead_history.length, zcr.dead_history.length);
      deadChart.data.labels = Array.from({ length: deadLen }, (_, i) => i + 1);
      deadChart.data.datasets[0].data = leach.dead_history;
      deadChart.data.datasets[1].data = zcr.dead_history;
      deadChart.update();

      const energyLen = Math.max(leach.energy_history.length, zcr.energy_history.length);
      energyChart.data.labels = Array.from({ length: energyLen }, (_, i) => i + 1);
      energyChart.data.datasets[0].data = leach.energy_history;
      energyChart.data.datasets[1].data = zcr.energy_history;
      energyChart.update();

      setWinnerHero(data.winner);
      updateMetricCards(leach, zcr);
      updateProtocolTile("leachTile", leach);
      updateProtocolTile("zcrTile", zcr);
      renderSummary(leach, zcr, data.winner);
    } catch (err) {
      const panel = byId("summaryPanel");
      if (panel) panel.innerHTML = `<p style="color:#ff9aa2;"><strong>Error:</strong> ${err.message}</p>`;
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = "Run Full Comparison";
    }
  });

  const compareCsvBtn = byId("compareCsvBtn");
  const compareJsonBtn = byId("compareJsonBtn");

  if (compareCsvBtn) compareCsvBtn.addEventListener("click", () => {
    window.location = "/export/compare/csv";
  });

  if (compareJsonBtn) compareJsonBtn.addEventListener("click", () => {
    window.location = "/export/compare/json";
  });
}

/* -------- simulation -------- */

function drawSimulation(state) {
  const canvas = byId("simCanvas");
  if (!canvas || !state) return;

  const ctx = canvas.getContext("2d");
  const cw = canvas.width;
  const ch = canvas.height;
  ctx.clearRect(0, 0, cw, ch);

  const scaleX = cw / state.width;
  const scaleY = ch / state.height;

  lastCanvasGeometry = { scaleX, scaleY, nodes: state.nodes };

  for (let x = 0; x < cw; x += 60) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, ch);
    ctx.strokeStyle = "rgba(255,255,255,0.035)";
    ctx.stroke();
  }
  for (let y = 0; y < ch; y += 60) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(cw, y);
    ctx.strokeStyle = "rgba(255,255,255,0.035)";
    ctx.stroke();
  }

  const bsx = state.base_station[0] * scaleX;
  const bsy = state.base_station[1] * scaleY;
  const zoneRadiusPx = state.zone_radius * scaleX;

  ctx.beginPath();
  ctx.arc(bsx, bsy, zoneRadiusPx, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(110,168,255,0.08)";
  ctx.fill();
  ctx.strokeStyle = "rgba(110,168,255,0.22)";
  ctx.lineWidth = 2;
  ctx.stroke();

  state.nodes.forEach(node => {
    if (!node.alive) return;
    const x = node.x * scaleX;
    const y = node.y * scaleY;

    if (node.target !== null && node.target !== undefined && state.nodes[node.target]) {
      const t = state.nodes[node.target];
      const tx = t.x * scaleX;
      const ty = t.y * scaleY;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(tx, ty);
      ctx.strokeStyle = node.ch ? "rgba(34,197,94,0.72)" : "rgba(180,194,230,0.35)";
      ctx.lineWidth = node.ch ? 1.8 : 1;
      ctx.stroke();
    } else if (node.ch) {
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(bsx, bsy);
      ctx.strokeStyle = "rgba(110,168,255,0.65)";
      ctx.lineWidth = 1.6;
      ctx.stroke();
    }
  });

  state.nodes.forEach(node => {
    const x = node.x * scaleX;
    const y = node.y * scaleY;

    let radius = 5;
    let color = "#f5f7ff";
    if (!node.alive) { radius = 4; color = "#ef4444"; }
    else if (node.ch) { radius = 8; color = "#22c55e"; }
    if (hoveredNode && hoveredNode.id === node.id) radius += 2;

    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();

    if (node.alive && !node.ch) {
      ctx.strokeStyle = "rgba(255,255,255,0.10)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  });

  ctx.fillStyle = "#6ea8ff";
  ctx.fillRect(bsx - 10, bsy - 10, 20, 20);
  ctx.fillStyle = "#dbe7ff";
  ctx.font = "bold 14px Inter, Arial";
  ctx.fillText("BS", bsx + 16, bsy + 5);
}

function updateSimMetrics(state) {
  if (!state) return;
  if (byId("metricProtocol")) byId("metricProtocol").textContent = state.protocol;
  if (byId("metricRound")) byId("metricRound").textContent = state.round;
  if (byId("metricAlive")) byId("metricAlive").textContent = state.alive;
  if (byId("metricDead")) byId("metricDead").textContent = state.dead;
  if (byId("metricEnergy")) byId("metricEnergy").textContent = state.total_energy.toFixed(4);
  if (byId("metricFND")) byId("metricFND").textContent = state.summary.first_dead_round ?? "-";
  if (byId("metricHND")) byId("metricHND").textContent = state.summary.half_dead_round ?? "-";
  if (byId("metricLND")) byId("metricLND").textContent = state.summary.last_dead_round ?? "-";
}

function updateMiniCharts(state) {
  if (!state) return;
  if (!miniAliveChart) miniAliveChart = buildMiniChart("miniAliveChart", "Alive Nodes", "#6ea8ff");
  if (!miniEnergyChart) miniEnergyChart = buildMiniChart("miniEnergyChart", "Energy", "#22d3ee");

  const labels = state.alive_history.map((_, i) => i + 1);
  miniAliveChart.data.labels = labels;
  miniAliveChart.data.datasets[0].data = state.alive_history;
  miniAliveChart.update();

  miniEnergyChart.data.labels = labels;
  miniEnergyChart.data.datasets[0].data = state.energy_history;
  miniEnergyChart.update();
}

function pushStateToHistory(state) {
  if (!state) return;
  const snapshot = JSON.parse(JSON.stringify(state));
  const last = simHistory[simHistory.length - 1];
  if (!last || last.round !== snapshot.round) simHistory.push(snapshot);
  updateTimelineSlider();
}

function updateTimelineSlider() {
  const slider = byId("timelineSlider");
  const label = byId("scrubberRoundLabel");
  if (!slider || !label) return;

  slider.max = Math.max(simHistory.length - 1, 0);
  slider.value = Math.max(simHistory.length - 1, 0);
  label.textContent = simHistory.length ? simHistory[simHistory.length - 1].round : "0";
}

function renderStateSnapshot(snapshot, sliderIndex = null) {
  if (!snapshot) return;
  currentSimState = snapshot;
  drawSimulation(snapshot);
  updateSimMetrics(snapshot);
  updateMiniCharts(snapshot);

  const label = byId("scrubberRoundLabel");
  if (label) label.textContent = snapshot.round;

  const slider = byId("timelineSlider");
  if (sliderIndex !== null && slider) slider.value = sliderIndex;
}

function stopSimTimer() {
  if (simTimer) { clearInterval(simTimer); simTimer = null; }
}
function stopReplayTimer() {
  if (replayTimer) { clearInterval(replayTimer); replayTimer = null; }
}

function hideTooltip() {
  const tooltip = byId("nodeTooltip");
  if (tooltip) tooltip.classList.add("hidden");
  hoveredNode = null;
}

function showTooltip(node, clientX, clientY) {
  const tooltip = byId("nodeTooltip");
  const canvas = byId("simCanvas");
  if (!tooltip || !canvas || !node) return;

  tooltip.innerHTML = `
    <div class="tooltip-title">Node ${node.id}</div>
    <div>Status: ${node.alive ? "Alive" : "Dead"}</div>
    <div>Cluster Head: ${node.ch ? "Yes" : "No"}</div>
    <div>Energy: ${Number(node.energy).toFixed(4)} J</div>
    <div>X: ${Number(node.x).toFixed(2)}</div>
    <div>Y: ${Number(node.y).toFixed(2)}</div>
  `;

  const rect = canvas.getBoundingClientRect();
  tooltip.style.left = `${clientX - rect.left}px`;
  tooltip.style.top = `${clientY - rect.top}px`;
  tooltip.classList.remove("hidden");
}

function bindCanvasHover() {
  const canvas = byId("simCanvas");
  if (!canvas) return;

  canvas.addEventListener("mousemove", (e) => {
    if (!lastCanvasGeometry || !currentSimState) return;

    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (canvas.width / rect.width);
    const my = (e.clientY - rect.top) * (canvas.height / rect.height);

    let found = null;
    currentSimState.nodes.forEach(node => {
      const x = node.x * lastCanvasGeometry.scaleX;
      const y = node.y * lastCanvasGeometry.scaleY;
      const radius = node.ch ? 10 : node.alive ? 7 : 6;
      const dx = mx - x;
      const dy = my - y;
      if (Math.sqrt(dx * dx + dy * dy) <= radius) found = node;
    });

    if (found) {
      hoveredNode = found;
      drawSimulation(currentSimState);
      showTooltip(found, e.clientX, e.clientY);
    } else {
      hideTooltip();
      drawSimulation(currentSimState);
    }
  });

  canvas.addEventListener("mouseleave", () => {
    hideTooltip();
    if (currentSimState) drawSimulation(currentSimState);
  });
}

function bindTimelineScrubber() {
  const slider = byId("timelineSlider");
  if (!slider) return;

  slider.addEventListener("input", () => {
    stopSimTimer();
    stopReplayTimer();
    const index = Number(slider.value);
    const snapshot = simHistory[index];
    if (snapshot) {
      renderStateSnapshot(snapshot, index);
      const simStatus = byId("simStatus");
      if (simStatus) simStatus.textContent = "Scrubbing";
    }
  });
}

function bindSimulationPage() {
  const startBtn = byId("startBtn");
  if (!startBtn) return;

  const protocolSelect = byId("protocolSelect");
  const seedInput = byId("seedInput");
  const speedInput = byId("speedInput");
  const simStatus = byId("simStatus");

  bindCanvasHover();
  bindTimelineScrubber();

  startBtn.addEventListener("click", async () => {
    stopSimTimer();
    stopReplayTimer();
    simHistory = [];

    currentSimState = await postJSON("/api/start", {
      protocol: protocolSelect.value,
      seed: Number(seedInput.value || 42)
    });

    pushStateToHistory(currentSimState);
    simStatus.textContent = "Started";
    renderStateSnapshot(currentSimState, simHistory.length - 1);
  });

  byId("stepBtn").addEventListener("click", async () => {
    stopReplayTimer();
    currentSimState = await postJSON("/api/step", {
      protocol: protocolSelect.value,
      steps: 1
    });
    pushStateToHistory(currentSimState);
    simStatus.textContent = "Stepping";
    renderStateSnapshot(currentSimState, simHistory.length - 1);
  });

  byId("playBtn").addEventListener("click", async () => {
    stopSimTimer();
    stopReplayTimer();

    currentSimState = await postJSON("/api/state", {
      protocol: protocolSelect.value
    });

    if (!simHistory.length || simHistory[simHistory.length - 1].round !== currentSimState.round) {
      pushStateToHistory(currentSimState);
    }

    renderStateSnapshot(currentSimState, simHistory.length - 1);
    simStatus.textContent = "Playing";

    simTimer = setInterval(async () => {
      currentSimState = await postJSON("/api/step", {
        protocol: protocolSelect.value,
        steps: 1
      });

      pushStateToHistory(currentSimState);
      renderStateSnapshot(currentSimState, simHistory.length - 1);

      if (currentSimState.finished) {
        simStatus.textContent = "Finished";
        stopSimTimer();
      }
    }, Number(speedInput.value || 180));
  });

  byId("pauseBtn").addEventListener("click", () => {
    stopSimTimer();
    stopReplayTimer();
    simStatus.textContent = "Paused";
  });

  byId("resetBtn").addEventListener("click", async () => {
    stopSimTimer();
    stopReplayTimer();
    simHistory = [];

    currentSimState = await postJSON("/api/reset", {
      protocol: protocolSelect.value,
      seed: Number(seedInput.value || 42)
    });

    pushStateToHistory(currentSimState);
    simStatus.textContent = "Reset";
    renderStateSnapshot(currentSimState, simHistory.length - 1);
  });

  byId("replayBtn").addEventListener("click", () => {
    stopSimTimer();
    stopReplayTimer();
    if (!simHistory.length) return;

    let index = 0;
    simStatus.textContent = "Replay";

    replayTimer = setInterval(() => {
      if (index >= simHistory.length) {
        stopReplayTimer();
        simStatus.textContent = "Replay Finished";
        return;
      }
      renderStateSnapshot(simHistory[index], index);
      index += 1;
    }, Math.max(70, Number(speedInput.value || 180)));
  });

  byId("csvBtn").addEventListener("click", () => {
    window.location = `/export/csv/${protocolSelect.value}`;
  });

  byId("jsonBtn").addEventListener("click", () => {
    window.location = `/export/json/${protocolSelect.value}`;
  });

  postJSON("/api/start", {
    protocol: protocolSelect.value,
    seed: Number(seedInput.value || 42)
  }).then((data) => {
    currentSimState = data;
    simHistory = [];
    pushStateToHistory(data);
    renderStateSnapshot(data, simHistory.length - 1);
  }).catch(() => {});
}

document.addEventListener("DOMContentLoaded", () => {
  revealOnScroll();
  animateCounters();
  bindSimulationPage();
  bindAnalysisPage();
});
