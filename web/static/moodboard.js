// Moodboard canvas: scatters captured brand images on a pannable board.
// Layout is seeded by the scan id so the default arrangement is stable
// across reloads; "shuffle" re-seeds it.
(() => {
  const canvas = document.querySelector("[data-moodboard]");
  const dataNode = document.querySelector("[data-moodboard-items]");
  if (!canvas || !dataNode) return;

  let items = [];
  try {
    items = JSON.parse(dataNode.textContent || "[]");
  } catch {
    return;
  }
  if (!Array.isArray(items) || items.length === 0) return;

  // mulberry32: tiny deterministic PRNG, enough for layout jitter.
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

  const ROLE_WIDTH = { social_card: 30, logo: 13, content: 22 };
  let zTop = 10;

  const layout = (seed) => {
    const rand = mulberry32(seed);
    // Spread tiles over shuffled grid cells, then jitter inside each cell
    // so the cloud never piles every image on the same spot.
    const cols = Math.ceil(Math.sqrt(items.length));
    const rows = Math.ceil(items.length / cols);
    const cells = [];
    for (let i = 0; i < cols * rows; i += 1) cells.push(i);
    for (let i = cells.length - 1; i > 0; i -= 1) {
      const j = Math.floor(rand() * (i + 1));
      [cells[i], cells[j]] = [cells[j], cells[i]];
    }
    return items.map((item, index) => {
      const cell = cells[index % cells.length];
      const col = cell % cols;
      const row = Math.floor(cell / cols);
      const width = (ROLE_WIDTH[item.role] || 20) + rand() * 5;
      const x = (col + 0.12 + rand() * 0.5) * (100 / cols);
      const y = (row + 0.12 + rand() * 0.5) * (100 / rows);
      const rotation = (rand() - 0.5) * 12;
      return {
        width,
        x: Math.min(x, 98 - width),
        y: Math.min(y, 86),
        rotation,
      };
    });
  };

  const applyLayout = (seed) => {
    const positions = layout(seed);
    canvas.querySelectorAll(".moodboard-item").forEach((tile) => {
      const pos = positions[Number(tile.dataset.index)];
      if (!pos) return;
      tile.style.width = `${pos.width}%`;
      tile.style.left = `${pos.x}%`;
      tile.style.top = `${pos.y}%`;
      tile.style.setProperty("--moodboard-rotation", `${pos.rotation.toFixed(2)}deg`);
      tile.style.transform = "";
      tile.dataset.dx = "0";
      tile.dataset.dy = "0";
    });
  };

  items.forEach((item, index) => {
    const tile = document.createElement("figure");
    tile.className = "moodboard-item";
    tile.dataset.index = String(index);
    tile.dataset.role = item.role || "content";

    const img = document.createElement("img");
    img.src = item.url;
    img.alt = item.alt || "";
    img.loading = "lazy";
    img.referrerPolicy = "no-referrer";
    img.draggable = false;
    img.addEventListener("error", () => tile.remove());

    const caption = document.createElement("figcaption");
    caption.className = "moodboard-caption";
    caption.textContent = item.host || "";

    tile.append(img, caption);
    canvas.append(tile);

    tile.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      zTop += 1;
      tile.style.zIndex = String(zTop);
      tile.classList.add("moodboard-item-grabbed");
      tile.setPointerCapture(event.pointerId);
      const startX = event.clientX;
      const startY = event.clientY;
      const baseX = Number(tile.dataset.dx || "0");
      const baseY = Number(tile.dataset.dy || "0");

      const onMove = (move) => {
        const dx = baseX + (move.clientX - startX);
        const dy = baseY + (move.clientY - startY);
        tile.dataset.dx = String(dx);
        tile.dataset.dy = String(dy);
        tile.style.transform = `translate(${dx}px, ${dy}px)`;
      };
      const onUp = () => {
        tile.classList.remove("moodboard-item-grabbed");
        tile.removeEventListener("pointermove", onMove);
        tile.removeEventListener("pointerup", onUp);
        tile.removeEventListener("pointercancel", onUp);
      };
      tile.addEventListener("pointermove", onMove);
      tile.addEventListener("pointerup", onUp);
      tile.addEventListener("pointercancel", onUp);
    });
  });

  const baseSeed = Number(canvas.dataset.moodboardSeed || "1") || 1;
  applyLayout(baseSeed);

  const shuffleButton = document.querySelector("[data-moodboard-shuffle]");
  if (shuffleButton) {
    shuffleButton.addEventListener("click", () => {
      applyLayout(Math.floor(Math.random() * 0xffffffff));
    });
  }
})();
