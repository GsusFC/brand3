// Brand3 rotating image cloud — a shared 3D-ish cloud engine used by both the
// scan loader (precarga) and the report moodboard. Cards are scattered on a
// jittered sphere, projected with perspective, and the whole cloud rotates with
// drag + inertia (and gentle ambient spin when idle). Wheel zooms. Cards fly
// into place on (re)layout, can fill progressively with imagery, and come alive
// (chromatic-aberration glitch) under the cursor. Exposes window.Brand3Cloud.
(() => {
  const NS = "http://www.w3.org/2000/svg";

  const mulberry32 = (seed) => {
    let a = seed >>> 0;
    return () => {
      a |= 0;
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };

  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

  // RGB channel-split filters for the hover glitch (injected once).
  const ensureFilters = () => {
    if (document.getElementById("b3-ca-red")) return;
    const svg = document.createElementNS(NS, "svg");
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
  };

  const ASPECTS = [4 / 3, 3 / 4, 1, 16 / 10, 3 / 2, 2 / 3];

  function mount(stage, opts) {
    opts = opts || {};
    ensureFilters();
    const layer = stage.querySelector("[data-cloud-layer]") || stage;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const interactive = opts.interactive !== false;
    const autoRotate = opts.autoRotate !== false;
    const focal = 2.6;

    let cards = [];
    let seen = new Set();
    let rotY = 0.4;
    let rotX = -0.12;
    let velY = 0;
    let zoom = opts.zoom || 1;
    let dragging = false;
    let lastX = 0;
    let lastY = 0;
    let rafId = 0;
    let visible = true;

    const unit = () => Math.min(stage.clientWidth, stage.clientHeight) || 320;

    const makeCard = (seedRand) => {
      const fig = document.createElement("figure");
      fig.className = "cloud-card";
      const img = document.createElement("span");
      img.className = "cloud-card-img";
      fig.appendChild(img);
      layer.appendChild(fig);
      const aspect = ASPECTS[(seedRand() * ASPECTS.length) | 0];
      const card = {
        el: fig,
        img,
        url: null,
        filled: false,
        alive: false,
        aspect,
        baseScale: 0.78 + seedRand() * 0.55,
        // current + target cloud positions (lerped for fly-in / reshuffle)
        px: 0, py: 0, pz: 0,
        tx: 0, ty: 0, tz: 0,
      };
      if (interactive) {
        fig.addEventListener("pointerenter", () => { card.alive = true; });
        fig.addEventListener("pointerleave", () => { card.alive = false; });
      }
      return card;
    };

    const sizeCard = (card) => {
      const u = unit();
      const w = u * 0.26 * card.baseScale * Math.sqrt(card.aspect);
      card.w = w;
      card.h = w / card.aspect;
      card.el.style.width = `${w.toFixed(1)}px`;
      card.el.style.height = `${card.h.toFixed(1)}px`;
    };

    const layout = (seed, { flyIn } = {}) => {
      const rng = mulberry32(seed || 1);
      const n = cards.length;
      const golden = Math.PI * (1 + Math.sqrt(5));
      cards.forEach((card, i) => {
        const t = (i + 0.5) / n;
        const phi = Math.acos(1 - 2 * t);
        const theta = golden * i;
        let x = Math.sin(phi) * Math.cos(theta);
        let y = Math.sin(phi) * Math.sin(theta);
        let z = Math.cos(phi);
        x += (rng() - 0.5) * 0.4;
        y += (rng() - 0.5) * 0.4;
        z += (rng() - 0.5) * 0.4;
        card.tx = x * 1.18;
        card.ty = y * 0.82;
        card.tz = z * 0.92;
        if (flyIn || reduced) {
          if (reduced) {
            card.px = card.tx; card.py = card.ty; card.pz = card.tz;
          } else {
            // start pushed outward + back, then lerp inward
            card.px = card.tx * 2.4;
            card.py = card.ty * 2.4;
            card.pz = card.tz - 1.8;
          }
        }
        sizeCard(card);
      });
    };

    const assign = (card, url) => {
      // Claim the slot synchronously so a burst of addImages() in one tick
      // doesn't all target the same still-empty card while the image loads.
      card.url = url;
      const probe = new Image();
      probe.referrerPolicy = "no-referrer";
      probe.onload = () => {
        card.img.style.setProperty("--cell-img", `url("${url}")`);
        card.el.classList.add("is-filled");
        card.filled = true;
        if (typeof opts.onFill === "function") opts.onFill(seen.size);
      };
      probe.onerror = () => { card.url = null; card.filled = false; seen.delete(url); };
      probe.src = url;
    };

    const ensureCards = (count, seedRand) => {
      while (cards.length < count) cards.push(makeCard(seedRand));
    };

    const render = () => {
      const cx = stage.clientWidth / 2;
      const cy = stage.clientHeight / 2;
      const spreadX = stage.clientWidth * 0.4;
      const spreadY = stage.clientHeight * 0.4;
      const ambient = autoRotate && !reduced && !dragging ? 0.0017 : 0;
      rotY += velY + ambient;
      if (!dragging) velY *= 0.93;
      if (Math.abs(velY) < 0.0002) velY = 0;
      rotX += (-0.12 - rotX) * 0.04;

      const cosY = Math.cos(rotY);
      const sinY = Math.sin(rotY);
      const cosX = Math.cos(rotX);
      const sinX = Math.sin(rotX);

      cards.forEach((card) => {
        // ease current cloud position toward target (fly-in / reshuffle)
        card.px += (card.tx - card.px) * 0.07;
        card.py += (card.ty - card.py) * 0.07;
        card.pz += (card.tz - card.pz) * 0.07;

        const x1 = card.px * cosY + card.pz * sinY;
        const z1 = -card.px * sinY + card.pz * cosY;
        const y1 = card.py * cosX - z1 * sinX;
        const z2 = card.py * sinX + z1 * cosX;

        const persp = focal / (focal - z2);
        const sx = cx + x1 * spreadX * persp * zoom;
        const sy = cy + y1 * spreadY * persp * zoom;
        const depth = clamp((z2 + 1.2) / 2.4, 0, 1);
        let scale = persp * zoom * (0.55 + depth * 0.5);
        if (card.alive) scale *= 1.18;

        card.el.style.transform =
          `translate3d(${(sx - card.w / 2).toFixed(1)}px, ${(sy - card.h / 2).toFixed(1)}px, 0) ` +
          `scale(${scale.toFixed(3)})`;
        card.el.style.opacity = (0.45 + depth * 0.55).toFixed(2);
        card.el.style.zIndex = card.alive ? 9999 : Math.round(depth * 1000);
        card.el.style.filter = depth < 0.45 ? `blur(${((0.45 - depth) * 2.4).toFixed(1)}px)` : "none";
      });

      rafId = visible ? requestAnimationFrame(render) : 0;
    };

    const start = () => { if (!rafId && visible) rafId = requestAnimationFrame(render); };
    const stop = () => { if (rafId) { cancelAnimationFrame(rafId); rafId = 0; } };

    // --- interaction ---------------------------------------------------------
    if (interactive) {
      stage.addEventListener("pointerdown", (e) => {
        dragging = true;
        velY = 0;
        lastX = e.clientX;
        lastY = e.clientY;
        try { stage.setPointerCapture(e.pointerId); } catch {}
      });
      stage.addEventListener("pointermove", (e) => {
        if (!dragging) return;
        const dx = e.clientX - lastX;
        const dy = e.clientY - lastY;
        rotY += dx * 0.006;
        rotX = clamp(rotX + dy * 0.004, -0.7, 0.7);
        velY = dx * 0.006;
        lastX = e.clientX;
        lastY = e.clientY;
      });
      const endDrag = () => { dragging = false; };
      stage.addEventListener("pointerup", endDrag);
      stage.addEventListener("pointercancel", endDrag);
      if (opts.allowZoom !== false) {
        stage.addEventListener("wheel", (e) => {
          e.preventDefault();
          zoom = clamp(zoom * (1 - e.deltaY * 0.0012), 0.55, 2.6);
        }, { passive: false });
      }
    }

    // --- controller API ------------------------------------------------------
    const controller = {
      setImages(items) {
        const rng = mulberry32((items && items.length) || 7);
        ensureCards(items.length, rng);
        // trim extras
        while (cards.length > items.length) cards.pop().el.remove();
        layout((items.length || 1) * 13 + 1, { flyIn: true });
        seen = new Set();
        items.forEach((item, i) => {
          const url = item && typeof item === "object" ? item.url : item;
          if (typeof url === "string" && url && !seen.has(url)) {
            seen.add(url);
            assign(cards[i], url);
          }
        });
        start();
      },
      addImages(items) {
        let added = false;
        (items || []).forEach((item) => {
          const url = item && typeof item === "object" ? item.url : item;
          if (typeof url !== "string" || !url || seen.has(url)) return;
          const slot = cards.find((c) => !c.url);
          if (!slot) return;
          seen.add(url);
          assign(slot, url);
          added = true;
        });
        return added;
      },
      buildPlaceholders(count) {
        const rng = mulberry32(count * 17 + 3);
        ensureCards(count, rng);
        layout(count * 13 + 1, { flyIn: true });
        start();
      },
      reshuffle() {
        layout(((Math.random() * 1e9) | 0) + 1, { flyIn: false });
      },
      setVisible(next) {
        visible = next;
        if (visible) start();
        else stop();
      },
      relayout() {
        cards.forEach(sizeCard);
      },
      get count() { return seen.size; },
    };

    window.addEventListener("resize", () => controller.relayout());
    return controller;
  }

  window.Brand3Cloud = { mount };
})();
