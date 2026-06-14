(() => {
  const root = document.querySelector("[data-status-waiting]");
  if (!root) return;

  const status = root.getAttribute("data-status") || "";
  const isPlayground = status === "playground";
  if (status !== "queued" && status !== "running" && !isPlayground) return;

  const canvas = root.querySelector("[data-dino-canvas]");
  const startButton = root.querySelector("[data-dino-start]");
  const scoreNode = root.querySelector("[data-dino-score]");
  const bestNode = root.querySelector("[data-dino-best]");
  const speedNode = root.querySelector("[data-dino-speed]");
  const levelNode = root.querySelector("[data-dino-level]");
  const stateNode = root.querySelector("[data-dino-state]");
  if (
    !(canvas instanceof HTMLCanvasElement) ||
    !startButton ||
    !scoreNode ||
    !bestNode ||
    !speedNode ||
    !levelNode ||
    !stateNode
  ) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const lang = canvas.getAttribute("data-game-lang") === "en" ? "en" : "es";
  const copy = {
    es: {
      start: "Empezar",
      pause: "Pausar",
      resume: "Seguir",
      running: "Corriendo",
      ready: "Listo para jugar",
      jump: "Saltando",
      doubleJump: "Doble salto",
      paused: "Pausado",
      hidden: "Pausado fuera de vista",
      reduced: "Movimiento reducido - pulsa Empezar",
      reducedRunning: "Movimiento reducido",
      crashed: "Choque. Pulsa Empezar para reintentar.",
      gameOver: "Fin de partida",
      retry: "Pulsa Empezar o Espacio para reintentar",
      resumeHint: "Pulsa Empezar, Espacio o P para seguir",
      signal: "+15 señal",
      level: "Nivel",
    },
    en: {
      start: "Start",
      pause: "Pause",
      resume: "Resume",
      running: "Running",
      ready: "Ready to play",
      jump: "Jumping",
      doubleJump: "Double jump",
      paused: "Paused",
      hidden: "Paused off-screen",
      reduced: "Motion reduced - tap Start",
      reducedRunning: "Motion reduced",
      crashed: "Crashed. Press Start to retry.",
      gameOver: "Game over",
      retry: "Press Start or Space to try again",
      resumeHint: "Press Start, Space, or P to resume",
      signal: "+15 signal",
      level: "Level",
    },
  }[lang];

  const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  const prefersReducedMotion = () => Boolean(reducedMotionQuery.matches);
  const pollInterval = Number(root.getAttribute("data-poll-interval")) || 5000;
  const readyHref = root.getAttribute("data-ready-href") || "";
  const bestStorageKey = "brand3-status-trex-best";

  const readBest = () => {
    try {
      return Number(window.localStorage.getItem(bestStorageKey)) || 0;
    } catch {
      return 0;
    }
  };

  const writeBest = (value) => {
    try {
      window.localStorage.setItem(bestStorageKey, String(Math.floor(value)));
    } catch {
      // Best score is optional; private storage should not break the status page.
    }
  };

  const state = {
    running: false,
    started: false,
    gameOver: false,
    userPaused: false,
    visible: true,
    rafId: 0,
    pollId: 0,
    lastTime: 0,
    score: 0,
    best: readBest(),
    level: 1,
    runTick: 0,
    speed: 4.2,
    obstacleTimer: 0,
    cloudTimer: 0,
    pickupTimer: 120,
    groundOffset: 0,
    jumpVelocity: 0,
    jumpsRemaining: 2,
    playerY: 0,
    playerBaseY: 126,
    obstacles: [],
    clouds: [],
    pickups: [],
  };

  const trex = {
    x: 58,
    width: 66,
    height: 71,
    sourceX: 672,
    sourceY: 2,
    sourceWidth: 44,
    sourceHeight: 47,
    frames: {
      jumping: 0,
      runningA: 88,
      runningB: 132,
      crashed: 176,
    },
  };

  // Original Chromium T-Rex spritesheet via wayou/t-rex-runner, BSD-3-Clause.
  const trexSpriteImage = new Image();
  const trexFrameCache = new Map();
  trexSpriteImage.src = "/static/vendor/t-rex-runner/offline-sprite-1x.png";
  trexSpriteImage.onload = () => {
    trexFrameCache.clear();
    render();
  };

  const css = getComputedStyle(document.documentElement);
  const palette = {
    background: css.getPropertyValue("--surface").trim() || "#f5f5f5",
    backgroundAlt: css.getPropertyValue("--surface-2").trim() || "#eeeeee",
    ground: css.getPropertyValue("--border").trim() || "#e4e4e4",
    dino: css.getPropertyValue("--olive").trim() || "#00ff00",
    hazard: css.getPropertyValue("--accent").trim() || "#ff0000",
    pickup: css.getPropertyValue("--olive").trim() || "#00ff00",
    text: css.getPropertyValue("--text").trim() || "#161616",
    muted: css.getPropertyValue("--text-muted").trim() || "#77736d",
  };

  const world = {
    width: canvas.width,
    height: canvas.height,
    groundY: 147,
    gravity: 0.62,
    jumpStrength: 12.8,
    doubleJumpStrength: 10.7,
    maxSpeed: 10.6,
  };

  const playerBox = () => ({
    x: trex.x + 4,
    y: state.playerY + 2,
    width: trex.width - 10,
    height: trex.height - 4,
  });

  const intersects = (a, b) => !(
    a.x + a.width < b.x ||
    a.x > b.x + b.width ||
    a.y + a.height < b.y ||
    a.y > b.y + b.height
  );

  const setStateMessage = (message) => {
    stateNode.textContent = message;
  };

  const setButton = () => {
    startButton.textContent = state.running ? copy.pause : state.started && !state.gameOver ? copy.resume : copy.start;
    startButton.setAttribute("aria-pressed", state.running ? "true" : "false");
  };

  const setHud = () => {
    const score = Math.max(0, Math.floor(state.score));
    if (score > state.best) {
      state.best = score;
      writeBest(score);
    }
    scoreNode.textContent = String(score);
    bestNode.textContent = String(Math.floor(state.best));
    speedNode.textContent = `x${Math.max(1, state.speed / 4.2).toFixed(1)}`;
    levelNode.textContent = `${copy.level} ${state.level}`;
  };

  const syncCanvasSize = () => {
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const scale = window.devicePixelRatio || 1;
    const nextWidth = Math.max(320, Math.round(rect.width * scale));
    const nextHeight = Math.max(130, Math.round(rect.height * scale));
    if (canvas.width !== nextWidth || canvas.height !== nextHeight) {
      canvas.width = nextWidth;
      canvas.height = nextHeight;
    }
    ctx.setTransform(canvas.width / rect.width, 0, 0, canvas.height / rect.height, 0, 0);
    world.width = rect.width;
    world.height = rect.height;
    world.groundY = Math.max(104, rect.height - 34);
    state.playerBaseY = world.groundY - trex.height;
  };

  const resetGame = () => {
    syncCanvasSize();
    state.running = true;
    state.started = true;
    state.gameOver = false;
    state.userPaused = false;
    state.lastTime = 0;
    state.score = 0;
    state.level = 1;
    state.speed = 4.2;
    state.runTick = 0;
    state.obstacleTimer = 32;
    state.cloudTimer = 18;
    state.pickupTimer = 120;
    state.groundOffset = 0;
    state.jumpVelocity = 0;
    state.jumpsRemaining = 2;
    state.playerY = state.playerBaseY;
    state.obstacles = [];
    state.clouds = [];
    state.pickups = [];
    setHud();
    setButton();
    setStateMessage(prefersReducedMotion() ? copy.reducedRunning : copy.running);
    if (state.rafId) {
      cancelAnimationFrame(state.rafId);
      state.rafId = 0;
    }
    state.rafId = requestAnimationFrame(tick);
  };

  const pause = (message, userInitiated = false) => {
    if (state.rafId) {
      cancelAnimationFrame(state.rafId);
      state.rafId = 0;
    }
    state.running = false;
    if (userInitiated) state.userPaused = true;
    if (message) setStateMessage(message);
    setButton();
  };

  const resume = () => {
    if (!state.started || state.gameOver || !state.visible || state.userPaused) return;
    if (state.running && state.rafId) return;
    state.running = true;
    state.lastTime = 0;
    setStateMessage(copy.running);
    setButton();
    state.rafId = requestAnimationFrame(tick);
  };

  const stopGame = (message) => {
    state.running = false;
    state.gameOver = true;
    state.userPaused = false;
    if (state.rafId) {
      cancelAnimationFrame(state.rafId);
      state.rafId = 0;
    }
    if (message) setStateMessage(message);
    setButton();
  };

  const spawnObstacle = () => {
    const roll = Math.random();
    const type = roll > 0.82 ? "wide" : roll > 0.48 ? "tall" : "short";
    const height = type === "wide" ? 28 : type === "tall" ? 34 : 20;
    const width = type === "wide" ? 28 : type === "tall" ? 15 : 13;
    state.obstacles.push({
      x: world.width + 18,
      y: world.groundY - height,
      width,
      height,
      type,
    });
  };

  const spawnPickup = () => {
    state.pickups.push({
      x: world.width + 22,
      y: world.groundY - 78 - Math.random() * 22,
      width: 12,
      height: 12,
      tick: 0,
    });
  };

  const spawnCloud = () => {
    state.clouds.push({
      x: world.width + 20,
      y: 24 + Math.random() * Math.max(24, world.height * 0.28),
      width: 36 + Math.random() * 26,
      speed: 0.35 + Math.random() * 0.25,
    });
  };

  const jump = () => {
    if (state.gameOver) {
      resetGame();
      return;
    }
    if (!state.started) {
      resetGame();
      return;
    }
    if (!state.running && state.userPaused) {
      state.userPaused = false;
      resume();
      return;
    }
    if (state.jumpsRemaining <= 0) return;
    const grounded = state.playerY >= state.playerBaseY - 0.5;
    state.jumpVelocity = grounded ? -world.jumpStrength : -world.doubleJumpStrength;
    state.jumpsRemaining -= 1;
    setStateMessage(grounded ? copy.jump : copy.doubleJump);
  };

  const drawBackground = () => {
    ctx.clearRect(0, 0, world.width, world.height);
    ctx.fillStyle = palette.background;
    ctx.fillRect(0, 0, world.width, world.height);

    ctx.fillStyle = palette.backgroundAlt;
    for (let x = 0; x < world.width; x += 48) {
      ctx.fillRect(x + ((state.groundOffset * -0.35) % 48), 0, 1, world.height);
    }

    ctx.strokeStyle = palette.ground;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(16, world.groundY + 0.5);
    ctx.lineTo(world.width - 16, world.groundY + 0.5);
    ctx.stroke();

    ctx.fillStyle = palette.ground;
    for (let i = 0; i < world.width; i += 26) {
      const x = 16 + ((i - state.groundOffset) % 26);
      ctx.fillRect(x, world.groundY + 7, 10, 1);
    }
  };

  const drawCloud = (cloud) => {
    ctx.fillStyle = palette.muted;
    ctx.globalAlpha = 0.45;
    ctx.fillRect(cloud.x, cloud.y, cloud.width, 2);
    ctx.fillRect(cloud.x + 8, cloud.y - 4, cloud.width - 16, 2);
    ctx.fillRect(cloud.x + 12, cloud.y + 4, cloud.width - 22, 2);
    ctx.globalAlpha = 1;
  };

  const drawObstacle = (obstacle) => {
    ctx.fillStyle = palette.hazard;
    if (obstacle.type === "wide") {
      ctx.fillRect(obstacle.x, obstacle.y + 8, obstacle.width, obstacle.height - 8);
      ctx.fillRect(obstacle.x + 4, obstacle.y, 6, obstacle.height);
      ctx.fillRect(obstacle.x + obstacle.width - 10, obstacle.y + 4, 6, obstacle.height - 4);
      return;
    }
    ctx.fillRect(obstacle.x, obstacle.y, obstacle.width, obstacle.height);
    ctx.fillRect(obstacle.x - 4, obstacle.y + 8, obstacle.width + 8, 4);
    ctx.fillRect(obstacle.x + 4, obstacle.y + 16, Math.max(3, obstacle.width - 8), 3);
  };

  const drawPickup = (pickup) => {
    const y = pickup.y + Math.sin(pickup.tick / 8) * 3;
    ctx.fillStyle = palette.pickup;
    ctx.fillRect(pickup.x + 4, y, 4, 12);
    ctx.fillRect(pickup.x, y + 4, 12, 4);
  };

  const tintTrexFrame = (frameX) => {
    const cacheKey = `${frameX}:${palette.dino}:${palette.background}`;
    if (trexFrameCache.has(cacheKey)) return trexFrameCache.get(cacheKey);
    if (!trexSpriteImage.complete || trexSpriteImage.naturalWidth === 0) return null;

    const frameCanvas = document.createElement("canvas");
    frameCanvas.width = trex.sourceWidth;
    frameCanvas.height = trex.sourceHeight;
    const frameCtx = frameCanvas.getContext("2d");
    if (!frameCtx) return null;

    frameCtx.imageSmoothingEnabled = false;
    frameCtx.drawImage(
      trexSpriteImage,
      trex.sourceX + frameX,
      trex.sourceY,
      trex.sourceWidth,
      trex.sourceHeight,
      0,
      0,
      trex.sourceWidth,
      trex.sourceHeight,
    );

    const imageData = frameCtx.getImageData(0, 0, trex.sourceWidth, trex.sourceHeight);
    const data = imageData.data;
    for (let index = 0; index < data.length; index += 4) {
      const isTransparent = data[index + 3] < 16;
      const isLightBackground = data[index] > 235 && data[index + 1] > 235 && data[index + 2] > 235;
      if (isTransparent || isLightBackground) {
        data[index + 3] = 0;
        continue;
      }
      data[index] = 0;
      data[index + 1] = 255;
      data[index + 2] = 0;
      data[index + 3] = 255;
    }
    frameCtx.putImageData(imageData, 0, 0);
    trexFrameCache.set(cacheKey, frameCanvas);
    return frameCanvas;
  };

  const drawDino = () => {
    const frame = state.gameOver ? 0 : Math.floor(state.runTick / 9) % 2;
    const jumpPose = state.jumpVelocity < 0 || state.playerY < state.playerBaseY - 2;
    const frameX = state.gameOver
      ? trex.frames.crashed
      : jumpPose
        ? trex.frames.jumping
        : frame === 0
          ? trex.frames.runningA
          : trex.frames.runningB;
    const frameImage = tintTrexFrame(frameX);
    if (!frameImage) return;

    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(frameImage, Math.round(trex.x), Math.round(state.playerY), trex.width, trex.height);
  };

  const drawOverlay = (title, subtitle) => {
    ctx.fillStyle = "rgba(245, 245, 245, 0.88)";
    if (document.documentElement.dataset.theme === "dark") {
      ctx.fillStyle = "rgba(18, 22, 21, 0.88)";
    }
    ctx.fillRect(0, 0, world.width, world.height);
    ctx.fillStyle = palette.text;
    ctx.font = "700 14px monospace";
    ctx.textAlign = "center";
    ctx.fillText(title, world.width / 2, world.height / 2 - 4);
    ctx.font = "12px sans-serif";
    ctx.fillText(subtitle, world.width / 2, world.height / 2 + 18);
  };

  const render = () => {
    drawBackground();
    state.clouds.forEach(drawCloud);
    state.pickups.forEach(drawPickup);
    state.obstacles.forEach(drawObstacle);
    drawDino();
    if (state.gameOver) drawOverlay(copy.gameOver, copy.retry);
    if (state.started && state.userPaused && !state.gameOver) drawOverlay(copy.paused, copy.resumeHint);
  };

  const update = (dt) => {
    if (!state.running || state.gameOver) return;
    const step = Math.max(0.25, dt / 16.6667);

    state.runTick += step;
    state.score += 0.8 * step;
    state.level = Math.min(9, 1 + Math.floor(state.score / 140));
    state.speed = Math.min(world.maxSpeed, 4.2 + state.score / 245 + state.level * 0.08);
    state.groundOffset = (state.groundOffset + state.speed * step) % 26;

    state.jumpVelocity += world.gravity * step;
    state.playerY = Math.min(state.playerBaseY, state.playerY + state.jumpVelocity * step);
    if (state.playerY >= state.playerBaseY) {
      state.playerY = state.playerBaseY;
      state.jumpVelocity = 0;
      state.jumpsRemaining = 2;
    }

    state.obstacleTimer -= step;
    if (state.obstacleTimer <= 0) {
      spawnObstacle();
      const speedPressure = Math.max(0, 76 - state.speed * 6);
      state.obstacleTimer = 58 + speedPressure + Math.random() * (62 + speedPressure * 0.45);
    }

    state.pickupTimer -= step;
    if (state.pickupTimer <= 0 && state.score > 60) {
      spawnPickup();
      state.pickupTimer = 150 + Math.random() * 125;
    }

    state.cloudTimer -= step;
    if (state.cloudTimer <= 0) {
      spawnCloud();
      state.cloudTimer = 150 + Math.random() * 110;
    }

    state.obstacles.forEach((obstacle) => {
      obstacle.x -= state.speed * step;
    });
    state.pickups.forEach((pickup) => {
      pickup.x -= (state.speed * 0.92) * step;
      pickup.tick += step;
    });
    state.clouds.forEach((cloud) => {
      cloud.x -= cloud.speed * step;
    });

    state.obstacles = state.obstacles.filter((obstacle) => obstacle.x + obstacle.width > -12);
    state.clouds = state.clouds.filter((cloud) => cloud.x + cloud.width > -12);

    const player = playerBox();
    state.pickups = state.pickups.filter((pickup) => {
      if (intersects(player, pickup)) {
        state.score += 15;
        setStateMessage(copy.signal);
        return false;
      }
      return pickup.x + pickup.width > -12;
    });

    if (state.obstacles.some((obstacle) => intersects(player, obstacle))) {
      setHud();
      stopGame(copy.crashed);
      render();
      return;
    }

    setHud();
  };

  const tick = (time) => {
    if (!state.running || !state.visible) {
      state.rafId = 0;
      return;
    }
    if (!state.lastTime) state.lastTime = time;
    const elapsed = Math.min(32, Math.max(1, time - state.lastTime));
    state.lastTime = time;
    update(elapsed);
    render();
    state.rafId = requestAnimationFrame(tick);
  };

  const handleVisibility = () => {
    state.visible = document.visibilityState !== "hidden";
    if (state.visible) {
      resume();
    } else {
      pause(copy.hidden);
    }
  };

  const observeVisibility = () => {
    if (!("IntersectionObserver" in window)) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        state.visible = entry.isIntersecting;
        if (state.visible) {
          resume();
        } else {
          pause(copy.hidden);
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(canvas);
  };

  const onStart = () => {
    if (!state.started || state.gameOver) {
      resetGame();
      return;
    }
    if (state.running) {
      pause(copy.paused, true);
      render();
      return;
    }
    state.userPaused = false;
    resume();
  };

  const onJumpKey = () => {
    if (!state.started || state.gameOver) {
      resetGame();
      state.jumpVelocity = -world.jumpStrength;
      state.jumpsRemaining = 1;
      setStateMessage(copy.jump);
      return;
    }
    jump();
  };

  const onKeyDown = (event) => {
    if (event.code === "KeyP") {
      event.preventDefault();
      onStart();
      return;
    }
    if (event.code !== "Space" && event.code !== "ArrowUp") return;
    event.preventDefault();
    onJumpKey();
  };

  const onPointerDown = (event) => {
    event.preventDefault();
    onJumpKey();
  };

  syncCanvasSize();
  state.playerY = state.playerBaseY;
  setHud();
  setButton();
  window.addEventListener("resize", () => {
    syncCanvasSize();
    state.playerY = Math.min(state.playerY || state.playerBaseY, state.playerBaseY);
    render();
  });
  document.addEventListener("visibilitychange", handleVisibility);
  observeVisibility();
  window.addEventListener("keydown", onKeyDown, { passive: false });
  canvas.addEventListener("pointerdown", onPointerDown, { passive: false });
  startButton.addEventListener("click", onStart);
  if (reducedMotionQuery.addEventListener) {
    reducedMotionQuery.addEventListener("change", () => {
      setStateMessage(prefersReducedMotion() ? copy.reduced : copy.running);
    });
  }

  setStateMessage(prefersReducedMotion() ? copy.reduced : copy.running);
  if (!prefersReducedMotion()) {
    resetGame();
  } else {
    render();
  }

})();

// Live status engine: ticking elapsed, RGB progress bar (red -> blue -> green,
// the B3S mark order), and polling that actually re-renders the status area.
// The waiting game above keeps its own state: only [data-status-dynamic] swaps.
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
