/* ============================================================
   app.js  –  Global JS for FaceAttend
   ============================================================ */

// ── Live clock ─────────────────────────────────────────────
function updateClock() {
  const el = document.getElementById("clock");
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleTimeString("en-IN", {
    hour: "2-digit", minute: "2-digit", second: "2-digit"
  });
}
setInterval(updateClock, 1000);
updateClock();

// ── Sidebar toggle (mobile) ────────────────────────────────
function toggleSidebar() {
  document.getElementById("sidebar").classList.toggle("open");
}

// Close sidebar when clicking outside on mobile
document.addEventListener("click", function (e) {
  const sidebar = document.getElementById("sidebar");
  const burger  = document.querySelector(".burger");
  if (window.innerWidth <= 768 &&
      sidebar.classList.contains("open") &&
      !sidebar.contains(e.target) &&
      e.target !== burger) {
    sidebar.classList.remove("open");
  }
});

// ── DB health indicator ────────────────────────────────────
async function checkDBStatus() {
  const el = document.getElementById("db-status");
  if (!el) return;
  try {
    const res  = await fetch("/api/health");
    const json = await res.json();
    if (json.db) {
      el.innerHTML  = '<i class="fa-solid fa-circle-dot"></i> DB Online';
      el.style.color = "#22c55e";
    } else {
      el.innerHTML  = '<i class="fa-solid fa-circle-exclamation"></i> DB Offline';
      el.style.color = "#ef4444";
    }
  } catch {
    el.innerHTML  = '<i class="fa-solid fa-circle-exclamation"></i> DB Error';
    el.style.color = "#ef4444";
  }
}
checkDBStatus();
setInterval(checkDBStatus, 30000);   // re-check every 30s

// ── Flash auto-dismiss ─────────────────────────────────────
document.querySelectorAll(".flash").forEach(el => {
  setTimeout(() => {
    el.style.transition = "opacity .5s";
    el.style.opacity    = "0";
    setTimeout(() => el.remove(), 500);
  }, 5000);
});
