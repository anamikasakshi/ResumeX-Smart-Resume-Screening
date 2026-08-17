const canvas = document.getElementById("stars");
const ctx = canvas.getContext("2d");
let stars = [];

function resizeCanvas() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = innerWidth * dpr;
  canvas.height = innerHeight * dpr;
  canvas.style.width = innerWidth + "px";
  canvas.style.height = innerHeight + "px";
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
function makeStars() {
  stars = Array.from({length: Math.min(150, Math.floor(innerWidth / 7))}, () => ({
    x: Math.random() * innerWidth,
    y: Math.random() * innerHeight,
    speed: .15 + Math.random() * .75,
    size: .3 + Math.random() * 1.35,
    length: 5 + Math.random() * 18,
    opacity: .18 + Math.random() * .65
  }));
}
function animateStars() {
  ctx.clearRect(0, 0, innerWidth, innerHeight);
  for (const s of stars) {
    s.y += s.speed;
    s.x -= s.speed * .12;
    if (s.y > innerHeight + 25) {
      s.y = -20;
      s.x = Math.random() * innerWidth;
    }
    if (s.x < -20) s.x = innerWidth + 10;

    const grad = ctx.createLinearGradient(s.x, s.y, s.x - s.length * .5, s.y - s.length);
    grad.addColorStop(0, `rgba(255,255,255,${s.opacity})`);
    grad.addColorStop(1, "rgba(139,92,246,0)");
    ctx.strokeStyle = grad;
    ctx.lineWidth = s.size;
    ctx.beginPath();
    ctx.moveTo(s.x, s.y);
    ctx.lineTo(s.x - s.length * .5, s.y - s.length);
    ctx.stroke();
  }
  requestAnimationFrame(animateStars);
}
resizeCanvas(); makeStars(); animateStars();
addEventListener("resize", () => { resizeCanvas(); makeStars(); });

const input = document.getElementById("resumes");
const dropzone = document.getElementById("dropzone");
const fileList = document.getElementById("fileList");
const form = document.getElementById("screenForm");
const btn = document.getElementById("screenBtn");
const progress = document.querySelector("#progress div");
const results = document.getElementById("results");
const rankingList = document.getElementById("rankingList");
const processed = document.getElementById("processed");
const errorBox = document.getElementById("errorBox");

document.querySelectorAll(".quick-tags button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.getElementById("jobDescription").value = btn.dataset.fill;
  });
});

function renderFiles(files) {
  fileList.innerHTML = "";
  [...files].forEach(file => {
    const row = document.createElement("div");
    row.className = "file-item";
    row.innerHTML = `<span>◈ ${escapeHtml(file.name)}</span><b>${formatSize(file.size)}</b>`;
    fileList.appendChild(row);
  });
}
function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes/1024).toFixed(1) + " KB";
  return (bytes/1024/1024).toFixed(1) + " MB";
}
input.addEventListener("change", () => renderFiles(input.files));
["dragenter","dragover"].forEach(ev => dropzone.addEventListener(ev, e => {
  e.preventDefault(); dropzone.classList.add("drag");
}));
["dragleave","drop"].forEach(ev => dropzone.addEventListener(ev, e => {
  e.preventDefault(); dropzone.classList.remove("drag");
}));
dropzone.addEventListener("drop", e => {
  if (e.dataTransfer.files.length) {
    input.files = e.dataTransfer.files;
    renderFiles(input.files);
  }
});

form.addEventListener("submit", async e => {
  e.preventDefault();
  btn.disabled = true;
  progress.style.width = "25%";
  errorBox.classList.add("hidden");
  results.classList.remove("hidden");
  rankingList.innerHTML = `<div style="color:#7f899b;font-size:12px;padding:30px;text-align:center">Analyzing resumes and building candidate ranking...</div>`;

  const data = new FormData(form);
  try {
    progress.style.width = "65%";
    const response = await fetch("/api/rank", { method:"POST", body:data });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Screening failed.");
    progress.style.width = "100%";
    renderResults(payload);
    results.scrollIntoView({behavior:"smooth", block:"start"});
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.classList.remove("hidden");
    rankingList.innerHTML = "";
  } finally {
    setTimeout(() => { btn.disabled = false; progress.style.width = "0"; }, 600);
  }
});

function renderResults(data) {
  processed.textContent = `${data.processed} candidate${data.processed === 1 ? "" : "s"} analyzed`;
  const badge = document.getElementById("modeBadge");
  badge.textContent = data.genai_mode ? "LOCAL LLM + RAG" : "RAG + EXPLAINER";
  let html = "";
  data.results.forEach((c) => {
    const matched = c.matched_skills.slice(0, 8).map(s => `<span class="tag good">${escapeHtml(s)}</span>`).join("");
    const missing = c.missing_skills.slice(0, 5).map(s => `<span class="tag missing">− ${escapeHtml(s)}</span>`).join("");
    const evidence = (c.evidence || []).map(e => `<p>${escapeHtml(e)}</p>`).join("");
    html += `
      <article class="candidate">
        <div class="rank">#${c.rank}</div>
        <div>
          <div class="candidate-name">${escapeHtml(c.name)}</div>
          <div class="candidate-file">${escapeHtml(c.file)}${c.contact.email ? " • " + escapeHtml(c.contact.email) : ""}</div>
          <div class="tags">${matched}${missing}</div>
        </div>
        <div class="score">
          <div class="score-number">${c.score}%</div>
          <div class="score-label">overall match</div>
          <div class="bar"><i style="width:${c.score}%"></i></div>
        </div>
        <div class="metrics">
          <div class="metric"><span>Relevance</span><b>${c.match}%</b></div>
          <div class="metric"><span>Skills</span><b>${c.skill_score}%</b></div>
          <div class="metric"><span>Experience</span><b>${c.experience_score}% · ${c.experience_years} yrs</b></div>
        </div>
        <div class="ai-card">
          <div class="ai-head"><span>✦ AI RANKING EXPLANATION</span><b>${data.genai_mode ? "LOCAL LLM + RAG" : "EVIDENCE MODE"}</b></div>
          <div class="ai-text">${escapeHtml(c.ai_explanation || "No explanation generated.")}</div>
          <details class="evidence"><summary>View retrieved resume evidence</summary>${evidence}</details>
        </div>
      </article>`;
  });
  rankingList.innerHTML = html;
  if (data.errors?.length) {
    errorBox.innerHTML = data.errors.map(e => `Could not read <b>${escapeHtml(e.file)}</b>: ${escapeHtml(e.error)}`).join("<br>");
    errorBox.classList.remove("hidden");
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, c => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#039;"
  }[c]));
}
