// Live status engine: ticking elapsed, RGB progress bar (red -> blue -> green,
// the B3S mark order), and polling that actually re-renders the status area.
// The scan loader (scan_loader.js) keeps its own state: only the
// [data-status-dynamic] region swaps on each poll.
(() => {
  const root = document.querySelector("[data-status-waiting]");
  if (!root) return;

  const POLL_MS = Number(root.getAttribute("data-poll-interval")) || 5000;
  // Where the bar starts when a phase begins, and how far it may creep while
  // the phase lasts. Asymptotic: it never claims progress the pipeline hasn't made.
  const FLOORS = { queued: 2, collecting: 8, extracting: 40, interpreting: 66, scoring: 82, finalizing: 91 };
  const TARGETS = { queued: 6, collecting: 38, extracting: 64, interpreting: 80, scoring: 90, finalizing: 97 };

  let status = root.getAttribute("data-status") || "";
  let phase = root.getAttribute("data-phase") || "";
  let elapsed = Number(root.getAttribute("data-elapsed")) || 0;
  let progress = FLOORS[phase] ?? 2;

  const isWaiting = () => status === "queued" || status === "running";
  const formatElapsed = (totalSeconds) => {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
  };

  const paint = () => {
    const bar = root.querySelector("[data-progress-bar]");
    if (bar) bar.style.setProperty("--scan-progress", `${progress.toFixed(1)}%`);
    const label = root.querySelector("[data-elapsed-label]");
    if (label) label.textContent = formatElapsed(elapsed);
  };

  const tick = () => {
    if (!isWaiting()) return;
    elapsed += 1;
    const target = TARGETS[phase] ?? 60;
    progress = Math.min(target, progress + Math.max(0.04, (target - progress) * 0.02));
    paint();
  };

  const applyFetched = (doc) => {
    const fresh = doc.querySelector("[data-status-waiting]");
    if (!fresh) return;
    const newStatus = fresh.getAttribute("data-status") || "";
    const newPhase = fresh.getAttribute("data-phase") || "";
    if (newStatus === status && newPhase === phase) return;
    status = newStatus;
    phase = newPhase;
    root.setAttribute("data-status", status);
    root.setAttribute("data-phase", phase);
    const freshDynamic = fresh.querySelector("[data-status-dynamic]");
    const dynamic = root.querySelector("[data-status-dynamic]");
    if (freshDynamic && dynamic) dynamic.innerHTML = freshDynamic.innerHTML;
    if (FLOORS[phase] != null) progress = Math.max(progress, FLOORS[phase]);
    paint();
  };

  const poll = async () => {
    if (document.hidden || !isWaiting()) return;
    try {
      const response = await fetch(window.location.href, {
        cache: "no-store",
        credentials: "same-origin",
        redirect: "follow",
      });
      if (response.redirected && response.url) {
        progress = 100;
        paint();
        window.setTimeout(() => window.location.assign(response.url), 350);
        return;
      }
      const text = await response.text();
      applyFetched(new DOMParser().parseFromString(text, "text/html"));
    } catch {
      // Transient network noise: keep the page alive and try again.
    }
  };

  paint();
  window.setInterval(tick, 1000);
  window.setInterval(poll, POLL_MS);
})();
