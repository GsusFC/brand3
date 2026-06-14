// Generative scan loader for the in-flight waiting screen.
//
// A dark "scanner" stage boots with procedural film grain + RGB glitch, lays
// out a skeleton grid, then progressively fills the cells with the brand's real
// captured imagery as the /assets endpoint surfaces it. Cells drift, and come
// alive (displace + chromatic-aberration) under the cursor. The whole thing is
// decorative: it never blocks navigation and degrades to a calm fade under
// prefers-reduced-motion.
(() => {
  const loader = document.querySelector("[data-scan-loader]");
  if (!loader) return;

  const statusRoot = document.querySelector("[data-status-waiting]");
  const stage = loader.querySelector("[data-loader-stage]");
  const grid = loader.querySelector("[data-loader-grid]");
  const grain = loader.querySelector("[data-loader-grain]");
  const captionNode = loader.querySelector("[data-loader-caption]");
  const countNode = loader.querySelector("[data-loader-count]");
  if (!stage || !grid || !(grain instanceof HTMLCanvasElement)) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const assetsHref = loader.getAttribute("data-assets-href") || "";
  const pollMs = Number(loader.getAttribute("data-poll-interval")) || 2500;

  let captions = {};
  const captionData = loader.querySelector("[data-loader-captions]");
  if (captionData) {
    try {
      captions = JSON.parse(captionData.textContent || "{}");
    } catch {
      captions = {};
    }
  }

  // --- One-time SVG channel filters for the chromatic-aberration glitch ------
  if (!document.getElementById("b3-ca-red")) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", "0");
    svg.setAttribute("height", "0");
    svg.style.position = "absolute";
    svg.innerHTML =
      '<defs>' +
      '<filter id="b3-ca-red" x="-20%" y="-20%" width="140%" height="140%">' +
      '<feColorMatrix type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0"/></filter>' +
      '<filter id="b3-ca-cyan" x="-20%" y="-20%" width="140%" height="140%">' +
      '<feColorMatrix type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 1 0"/></filter>' +
      '</defs>';
    document.body.appendChild(svg);
  }

  // --- Grid construction -----------------------------------------------------
  const rand = (min, max) => min + Math.random() * (max - min);

  const buildGrid = () => {
    const rect = stage.getBoundingClientRect();
    const width = rect.width || 640;
    const height = rect.height || 320;
    const cols = Math.max(3, Math.min(6, Math.round(width / 150)));
    const rows = Math.max(2, Math.min(4, Math.round(height / 150)));
    grid.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
    grid.style.gridTemplateRows = `repeat(${rows}, 1fr)`;
    grid.textContent = "";
    const total = cols * rows;
    const cells = [];
    for (let i = 0; i < total; i += 1) {
      const cell = document.createElement("figure");
      cell.className = "scan-cell";
      cell.style.setProperty("--cell-delay", `${Math.round((i % cols) * 60 + Math.floor(i / cols) * 90)}ms`);
      cell.style.setProperty("--drift-dur", `${rand(13, 22).toFixed(1)}s`);
      const img = document.createElement("span");
      img.className = "scan-cell-img";
      cell.appendChild(img);
      grid.appendChild(cell);
      cells.push(cell);
    }
    return cells;
  };

  let cells = buildGrid();
  // Fill order: organic, center-biased shuffle so the picture assembles inward.
  const fillOrder = cells.map((_, i) => i).sort(() => Math.random() - 0.5);
  let nextFill = 0;
  const seen = new Set();

  const fillCell = (url) => {
    if (seen.has(url) || nextFill >= fillOrder.length) return false;
    const cell = cells[fillOrder[nextFill]];
    if (!cell) return false;
    seen.add(url);
    nextFill += 1;
    // Preload so the reveal animation runs on a decoded image (or skip on error).
    const probe = new Image();
    probe.referrerPolicy = "no-referrer";
    probe.onload = () => {
      const layer = cell.querySelector(".scan-cell-img");
      if (layer) layer.style.setProperty("--cell-img", `url("${url}")`);
      cell.classList.add("is-filled");
      if (countNode) countNode.textContent = String(seen.size);
    };
    probe.onerror = () => {
      // Roll back this slot so a working image can use it later.
      seen.delete(url);
      nextFill -= 1;
    };
    probe.src = url;
    return true;
  };

  // --- Hover: bring cells alive ---------------------------------------------
  const onPointerMove = (event) => {
    const cell = event.currentTarget;
    const rect = cell.getBoundingClientRect();
    const mx = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
    const my = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
    cell.style.setProperty("--mx", mx.toFixed(3));
    cell.style.setProperty("--my", my.toFixed(3));
  };
  const onPointerEnter = (event) => event.currentTarget.classList.add("is-alive");
  const onPointerLeave = (event) => {
    const cell = event.currentTarget;
    cell.classList.remove("is-alive");
    cell.style.setProperty("--mx", "0");
    cell.style.setProperty("--my", "0");
  };
  cells.forEach((cell) => {
    cell.addEventListener("pointerenter", onPointerEnter);
    cell.addEventListener("pointermove", onPointerMove);
    cell.addEventListener("pointerleave", onPointerLeave);
  });

  // --- Caption follows the pipeline phase -----------------------------------
  const syncCaption = () => {
    if (!captionNode || !statusRoot) return;
    const phase = statusRoot.getAttribute("data-phase") || "";
    const text = captions[phase];
    if (text && captionNode.textContent !== text) captionNode.textContent = text;
  };

  // --- Procedural grain + glitch --------------------------------------------
  const gctx = grain.getContext("2d");
  let noiseTile = null;
  let grainRaf = 0;
  let lastGrain = 0;
  let visible = true;

  const sizeGrain = () => {
    const rect = stage.getBoundingClientRect();
    // Render at half resolution; the blur of upscaling reads as fine grain.
    grain.width = Math.max(160, Math.round(rect.width / 2));
    grain.height = Math.max(120, Math.round(rect.height / 2));
    const tw = 96;
    const th = 72;
    noiseTile = gctx.createImageData(tw, th);
  };

  const drawNoise = () => {
    if (!gctx || !noiseTile) return;
    const data = noiseTile.data;
    for (let i = 0; i < data.length; i += 4) {
      const v = (Math.random() * 255) | 0;
      data[i] = data[i + 1] = data[i + 2] = v;
      data[i + 3] = (Math.random() * 46) | 0;
    }
    // Tile the small noise patch across the canvas.
    const tmp = document.createElement("canvas");
    tmp.width = noiseTile.width;
    tmp.height = noiseTile.height;
    tmp.getContext("2d").putImageData(noiseTile, 0, 0);
    const pattern = gctx.createPattern(tmp, "repeat");
    gctx.clearRect(0, 0, grain.width, grain.height);
    gctx.fillStyle = pattern;
    gctx.fillRect(0, 0, grain.width, grain.height);

    // Occasional RGB glitch bands.
    if (Math.random() < 0.22) {
      const bands = 1 + ((Math.random() * 3) | 0);
      gctx.globalCompositeOperation = "screen";
      for (let b = 0; b < bands; b += 1) {
        const y = (Math.random() * grain.height) | 0;
        const h = 1 + ((Math.random() * 6) | 0);
        const off = 2 + ((Math.random() * 8) | 0);
        gctx.fillStyle = "rgba(255,0,40,0.5)";
        gctx.fillRect(-off, y, grain.width, h);
        gctx.fillStyle = "rgba(0,225,255,0.5)";
        gctx.fillRect(off, y + 1, grain.width, h);
      }
      gctx.globalCompositeOperation = "source-over";
    }
  };

  const grainLoop = (time) => {
    if (!visible) {
      grainRaf = 0;
      return;
    }
    if (time - lastGrain > 80) {
      drawNoise();
      lastGrain = time;
    }
    grainRaf = requestAnimationFrame(grainLoop);
  };

  const startGrain = () => {
    if (reducedMotion.matches) {
      drawNoise();
      return;
    }
    if (!grainRaf) {
      lastGrain = 0;
      grainRaf = requestAnimationFrame(grainLoop);
    }
  };
  const stopGrain = () => {
    if (grainRaf) {
      cancelAnimationFrame(grainRaf);
      grainRaf = 0;
    }
  };

  // --- Asset polling ---------------------------------------------------------
  const isWaiting = () => {
    const status = statusRoot ? statusRoot.getAttribute("data-status") : "running";
    return status === "queued" || status === "running";
  };

  const pollAssets = async () => {
    if (!assetsHref || document.hidden || !isWaiting()) return;
    try {
      const res = await fetch(assetsHref, { cache: "no-store", credentials: "same-origin" });
      if (!res.ok) return;
      const data = await res.json();
      const images = Array.isArray(data.images) ? data.images : [];
      images.forEach((item) => {
        const url = item && typeof item === "object" ? item.url : item;
        if (typeof url === "string" && url) fillCell(url);
      });
    } catch {
      // Transient: try again next interval.
    }
  };

  // --- Lifecycle -------------------------------------------------------------
  const setVisible = (next) => {
    visible = next;
    if (visible) startGrain();
    else stopGrain();
  };

  sizeGrain();
  startGrain();
  syncCaption();
  pollAssets();
  window.setInterval(pollAssets, pollMs);
  window.setInterval(syncCaption, 1000);

  let resizeTimer = 0;
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(sizeGrain, 200);
  });
  document.addEventListener("visibilitychange", () => setVisible(!document.hidden));
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting && !document.hidden),
      { threshold: 0.05 },
    ).observe(stage);
  }
  if (reducedMotion.addEventListener) {
    reducedMotion.addEventListener("change", () => {
      stopGrain();
      startGrain();
    });
  }
})();
