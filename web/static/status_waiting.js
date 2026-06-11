(() => {
  const root = document.querySelector("[data-status-waiting]");
  if (!root) return;

  const status = root.getAttribute("data-status") || "";
  if (status !== "queued" && status !== "running") return;

  const canvas = root.querySelector("[data-dino-canvas]");
  const startButton = root.querySelector("[data-dino-start]");
  const scoreNode = root.querySelector("[data-dino-score]");
  const stateNode = root.querySelector("[data-dino-state]");
  if (!(canvas instanceof HTMLCanvasElement) || !startButton || !scoreNode || !stateNode) {
    return;
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  const prefersReducedMotion = () => Boolean(reducedMotionQuery.matches);
  const pollInterval = Number(root.getAttribute("data-poll-interval")) || 5000;
  const readyHref = root.getAttribute("data-ready-href") || "";

  const state = {
    running: false,
    started: false,
    gameOver: false,
    visible: true,
    rafId: 0,
    pollId: 0,
    lastTime: 0,
    lastPollAt: 0,
    score: 0,
    best: 0,
    runTick: 0,
    speed: 4.2,
    obstacleTimer: 0,
    cloudTimer: 0,
    groundOffset: 0,
    jumpVelocity: 0,
    playerY: 0,
    playerBaseY: 126,
    obstacles: [],
    clouds: [],
  };

  const trex = {
    x: 58,
    width: 44,
    height: 47,
    frame: {
      jumping: 0,
      runningA: 88,
      runningB: 132,
      crashed: 220,
    },
  };

  const trexImage = new Image();
  const trexFrameCache = new Map();
  trexImage.src = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQgAAAAvAgMAAABiRrxWAAAADFBMVEX///9TU1P39/f///+TS9URAAAAAXRSTlMAQObYZgAAAPpJREFUeF7d0jFKRkEMhdGLMM307itNLALyVmHvJuzTDMjdn72E95PGFEZSmeoU4YMMgxhskvQec8YSVFX1NhGcS5ywtbmC8khcZeKq+ZWJ4F8Sr2+ZCErjkJFEfcjAc/6/BMlfcz6xHdhRthYzIZhIHMcTVY1scUUiAphK8CMSPUbieTBhvD9Lj0vyV4wklEGzHpciKGOJoBp7XDcFs4kWxxM7Ey3iZ8JbzASAvMS7XLOJHTTvEkEZSeQl7DMuwVyCasqK5+XzQRYLUJlMbPXjFcn3m8eKBSjWZMJwvGIOvViAzCbUj1VEDoqFOEQGE3SyInJQLOQMJL4B7enP1UbLXJQAAAAASUVORK5CYII=";
  trexImage.onload = () => {
    trexFrameCache.clear();
    render();
  };

  const css = getComputedStyle(document.documentElement);
  const palette = {
    background: css.getPropertyValue("--surface").trim() || "#f5f5f5",
    ground: css.getPropertyValue("--border").trim() || "#e4e4e4",
    dino: "#050806",
    dinoOutline: "#4f8f5a",
    hazard: css.getPropertyValue("--accent").trim() || "#ff0000",
    text: css.getPropertyValue("--text").trim() || "#161616",
  };

  const world = {
    width: canvas.width,
    height: canvas.height,
    groundY: 147,
    gravity: 0.62,
    jumpStrength: 12.8,
    maxSpeed: 10.2,
  };

  const setStateMessage = (message) => {
    stateNode.textContent = message;
  };

  const setScore = (value) => {
    scoreNode.textContent = String(Math.max(0, value | 0));
  };

  const canJump = () => state.started && !state.gameOver && state.playerY >= state.playerBaseY - 0.5;

  const syncCanvasSize = () => {
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const scale = window.devicePixelRatio || 1;
    const nextWidth = Math.max(320, Math.round(rect.width * scale));
    const nextHeight = Math.max(90, Math.round(rect.height * scale));
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
    state.lastTime = 0;
    state.score = 0;
    state.speed = 4.2;
    state.runTick = 0;
    state.obstacleTimer = 0;
    state.cloudTimer = 0;
    state.groundOffset = 0;
    state.jumpVelocity = 0;
    state.playerY = state.playerBaseY;
    state.obstacles = [];
    state.clouds = [];
    setScore(0);
    setStateMessage(prefersReducedMotion() ? "Motion reduced" : "Running");
    if (state.rafId) {
      cancelAnimationFrame(state.rafId);
      state.rafId = 0;
    }
    requestAnimationFrame(tick);
  };

  const stopGame = (message) => {
    state.running = false;
    state.gameOver = true;
    if (state.rafId) {
      cancelAnimationFrame(state.rafId);
      state.rafId = 0;
    }
    if (message) setStateMessage(message);
  };

  const spawnObstacle = () => {
    const sizeRoll = Math.random();
    const type = sizeRoll > 0.86 ? "wide" : sizeRoll > 0.46 ? "tall" : "short";
    const height = type === "wide" ? 30 : type === "tall" ? 24 : 18;
    const width = type === "wide" ? 18 : type === "tall" ? 14 : 12;
    state.obstacles.push({
      x: world.width + 18,
      y: world.groundY - height,
      width,
      height,
      type,
    });
  };

  const spawnCloud = () => {
    state.clouds.push({
      x: world.width + 20,
      y: 24 + Math.random() * 42,
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
    if (canJump()) {
      state.jumpVelocity = -world.jumpStrength;
      setStateMessage("Jumping");
    }
  };

  const isColliding = (obstacle) => {
    const player = {
      x: trex.x + 6,
      y: state.playerY,
      width: trex.width - 10,
      height: trex.height,
    };
    return !(
      player.x + player.width < obstacle.x ||
      player.x > obstacle.x + obstacle.width ||
      player.y + player.height < obstacle.y ||
      player.y > obstacle.y + obstacle.height
    );
  };

  const drawBackground = () => {
    ctx.clearRect(0, 0, world.width, world.height);
    ctx.fillStyle = palette.background;
    ctx.fillRect(0, 0, world.width, world.height);

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
    ctx.fillStyle = palette.hazard;
    ctx.fillRect(cloud.x, cloud.y, cloud.width, 2);
    ctx.fillRect(cloud.x + 8, cloud.y - 4, cloud.width - 16, 2);
    ctx.fillRect(cloud.x + 12, cloud.y + 4, cloud.width - 22, 2);
  };

  const drawObstacle = (obstacle) => {
    ctx.fillStyle = palette.hazard;
    ctx.fillRect(obstacle.x, obstacle.y, obstacle.width, obstacle.height);
    ctx.fillRect(obstacle.x - 4, obstacle.y + 8, obstacle.width + 8, 4);
    ctx.fillRect(obstacle.x + 4, obstacle.y + 14, obstacle.width - 8, 3);
  };

  const tintTrexFrame = (sourceX) => {
    if (trexFrameCache.has(sourceX)) return trexFrameCache.get(sourceX);
    if (!trexImage.complete || trexImage.naturalWidth === 0) return null;

    const frameCanvas = document.createElement("canvas");
    frameCanvas.width = trex.width;
    frameCanvas.height = trex.height;
    const frameCtx = frameCanvas.getContext("2d");
    if (!frameCtx) return null;
    frameCtx.imageSmoothingEnabled = false;
    frameCtx.drawImage(trexImage, sourceX, 0, trex.width, trex.height, 0, 0, trex.width, trex.height);
    const imageData = frameCtx.getImageData(0, 0, trex.width, trex.height);
    const data = imageData.data;
    const bodyColor = { r: 5, g: 8, b: 6 };
    const outlineColor = { r: 79, g: 143, b: 90 };
    const mask = new Uint8Array(trex.width * trex.height);
    for (let index = 0; index < data.length; index += 4) {
      const isBackground = data[index] > 225 && data[index + 1] > 225 && data[index + 2] > 225;
      if (!isBackground) {
        mask[index / 4] = 1;
      }
    }
    for (let y = 0; y < trex.height; y += 1) {
      for (let x = 0; x < trex.width; x += 1) {
        const maskIndex = y * trex.width + x;
        const dataIndex = maskIndex * 4;
        if (!mask[maskIndex]) {
          data[dataIndex + 3] = 0;
          continue;
        }
        let isEdge = false;
        for (let oy = -1; oy <= 1 && !isEdge; oy += 1) {
          for (let ox = -1; ox <= 1; ox += 1) {
            const nx = x + ox;
            const ny = y + oy;
            if (nx < 0 || ny < 0 || nx >= trex.width || ny >= trex.height || !mask[ny * trex.width + nx]) {
              isEdge = true;
              break;
            }
          }
        }
        const color = isEdge ? outlineColor : bodyColor;
        data[dataIndex] = color.r;
        data[dataIndex + 1] = color.g;
        data[dataIndex + 2] = color.b;
        data[dataIndex + 3] = 255;
      }
    }
    frameCtx.putImageData(imageData, 0, 0);
    trexFrameCache.set(sourceX, frameCanvas);
    return frameCanvas;
  };

  const drawDino = () => {
    const x = trex.x;
    const y = state.playerY;
    const frame = state.gameOver ? 0 : Math.floor(state.runTick / 9) % 2;
    const jumpPose = state.jumpVelocity < 0 || state.playerY < state.playerBaseY - 2;
    const sourceX = state.gameOver
      ? trex.frame.crashed
      : jumpPose
        ? trex.frame.jumping
        : frame === 0
          ? trex.frame.runningA
          : trex.frame.runningB;
    const frameImage = tintTrexFrame(sourceX);
    if (!frameImage) return;
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(frameImage, x, y, trex.width, trex.height);
  };

  const drawGameOver = () => {
    ctx.fillStyle = "rgba(245, 245, 245, 0.88)";
    ctx.fillRect(0, 0, world.width, world.height);
    ctx.fillStyle = palette.text;
    ctx.font = "700 14px monospace";
    ctx.textAlign = "center";
    ctx.fillText("Game over", world.width / 2, world.height / 2 - 4);
    ctx.font = "12px sans-serif";
    ctx.fillText("Press Start or Space to try again", world.width / 2, world.height / 2 + 18);
  };

  const render = () => {
    drawBackground();
    state.clouds.forEach(drawCloud);
    state.obstacles.forEach(drawObstacle);
    drawDino();
    if (state.gameOver) drawGameOver();
  };

  const update = (dt) => {
    if (!state.running || state.gameOver) return;
    const step = Math.max(0.25, dt / 16.6667);

    state.runTick += step;
    state.score += 0.8 * step;
    state.best = Math.max(state.best, state.score);
    state.speed = Math.min(world.maxSpeed, 4.2 + state.score / 260);
    state.groundOffset = (state.groundOffset + state.speed * step) % 26;

    state.jumpVelocity += world.gravity * step;
    state.playerY = Math.min(
      state.playerBaseY,
      state.playerY + state.jumpVelocity * step,
    );
    if (state.playerY >= state.playerBaseY) {
      state.playerY = state.playerBaseY;
      state.jumpVelocity = 0;
    }

    state.obstacleTimer -= step;
    if (state.obstacleTimer <= 0) {
      spawnObstacle();
      const speedPressure = Math.max(0, 82 - state.speed * 6);
      state.obstacleTimer = 70 + speedPressure + Math.random() * (70 + speedPressure * 0.55);
    }

    state.cloudTimer -= step;
    if (state.cloudTimer <= 0) {
      spawnCloud();
      state.cloudTimer = 170 + Math.random() * 120;
    }

    state.obstacles.forEach((obstacle) => {
      obstacle.x -= state.speed * step;
    });
    state.clouds.forEach((cloud) => {
      cloud.x -= cloud.speed * step;
    });

    state.obstacles = state.obstacles.filter((obstacle) => obstacle.x + obstacle.width > -12);
    state.clouds = state.clouds.filter((cloud) => cloud.x + cloud.width > -12);

    if (state.obstacles.some(isColliding)) {
      setScore(Math.floor(state.score));
      stopGame("Crashed. Press Start to retry.");
      render();
      return;
    }

    setScore(Math.floor(state.score));
  };

  const tick = (time) => {
    if (!state.running || !state.visible) {
      state.rafId = 0;
      return;
    }
    if (!state.lastTime) {
      state.lastTime = time;
    }
    const elapsed = Math.min(32, Math.max(1, time - state.lastTime));
    state.lastTime = time;
    update(elapsed);
    render();
    state.rafId = requestAnimationFrame(tick);
  };

  const resume = () => {
    if (!state.started || state.gameOver || !state.visible) return;
    if (state.running && state.rafId) return;
    state.running = true;
    state.lastTime = 0;
    state.rafId = requestAnimationFrame(tick);
  };

  const pause = (message) => {
    if (state.rafId) {
      cancelAnimationFrame(state.rafId);
      state.rafId = 0;
    }
    state.running = false;
    if (message) setStateMessage(message);
  };

  const handleVisibility = () => {
    state.visible = document.visibilityState !== "hidden";
    if (state.visible) {
      resume();
    } else {
      pause("Paused while hidden");
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
          pause("Paused while off-screen");
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(canvas);
  };

  const requestRefresh = async () => {
    if (!readyHref && !window.location.pathname.includes("/status")) return;
    try {
      const response = await fetch(window.location.href, {
        cache: "no-store",
        credentials: "same-origin",
        redirect: "follow",
      });
      if (response.redirected && response.url) {
        window.location.assign(response.url);
      }
    } catch {
      // Keep the waiting page usable if polling fails transiently.
    }
  };

  const schedulePolling = () => {
    const run = async () => {
      if (document.hidden) return;
      await requestRefresh();
    };

    run();
    state.pollId = window.setInterval(run, pollInterval);
  };

  const onStart = () => {
    if (!state.started || state.gameOver) {
      resetGame();
      return;
    }
    jump();
  };

  const onJumpKey = () => {
    if (!state.started || state.gameOver) {
      resetGame();
      state.jumpVelocity = -world.jumpStrength;
      setStateMessage("Jumping");
      return;
    }
    jump();
  };

  const onKeyDown = (event) => {
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
      setStateMessage(prefersReducedMotion() ? "Motion reduced" : "Running");
    });
  }

  setStateMessage(prefersReducedMotion() ? "Motion reduced - tap Start" : "Running");
  if (!prefersReducedMotion()) {
    resetGame();
  } else {
    render();
  }

  schedulePolling();
})();
