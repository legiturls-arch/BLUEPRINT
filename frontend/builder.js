import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";

// --------------------------------------------------
// BLUEPRINT — 3D Engineering Builder
// --------------------------------------------------

const API = location.protocol === "file:"
  ? "http://127.0.0.1:8000"
  : location.origin;

const $ = id => document.getElementById(id);

// DOM helpers: every access to an optional element goes through these,
// so a missing element never throws.
function setText(id, text) {
  const el = $(id);
  if (el) el.textContent = text;
  return !!el;
}

function setHidden(id, hidden) {
  const el = $(id);
  if (el) el.hidden = hidden;
}

function on(id, eventName, handler) {
  const el = $(id);
  if (el) el.addEventListener(eventName, handler);
}

function showError(message) {
  console.error(message);

  const el = $("error");
  if (el) {
    el.hidden = false;
    el.textContent = message;
  }
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

const categoryLabels = {
  actuator: "Actuators",
  mechanical: "Mechanical",
  power: "Power",
  structure: "Structure",
  sensor: "Sensors",
  electrical: "Electrical",
  robotics: "Robotics",
  aerospace: "Aerospace",
  space: "Space"
};

const librarySectionLabels = {
  structure: "Structure",
  mechanical: "Mechanical",
  actuator: "Motors & Actuators",
  power: "Power System",
  sensor: "Sensors",
  lighting: "Lighting",
  space: "Space Components"
};

const categoryIcons = {
  actuator: "⚙",
  mechanical: "◉",
  power: "▣",
  structure: "▰",
  sensor: "⌁",
  electrical: "ϟ",
  robotics: "⬡",
  aerospace: "✦",
  space: "◌"
};

function librarySectionFor(component) {
  if (component.id === "rgb_led_unit") return "lighting";
  if (component.library === "space") return "space";
  if (component.category === "structure") return "structure";
  if (component.category === "mechanical") return "mechanical";
  if (component.category === "actuator") return "actuator";
  if (component.category === "power" || component.category === "electrical") {
    return "power";
  }
  if (component.category === "sensor") return "sensor";
  return "mechanical";
}

// Component groups the summary, simulation and driving code all share.
const MOTOR_IDS = ["motor_basic", "motor_geared"];
const WHEEL_IDS = ["wheel_basic", "space_rover_wheel"];
const isMotorPart = part => MOTOR_IDS.includes(part.componentId);
const isWheelPart = part => WHEEL_IDS.includes(part.componentId);

// Scale limits shared by the inspector input and the gizmo.
const SCALE_MIN = 0.05;
const SCALE_MAX = 20;

// Snapping: while moving, a part jumps onto the origin of another part
// closer than this distance (metres). It is not collision detection.
const SNAP_DISTANCE = 0.25;

// The inspector only edits yaw (rotation about Y), so the Rotate gizmo
// is limited to the Y ring. Set to false to allow tilting on X and Z.
const ROTATE_Y_ONLY = true;

// Honest placeholder texts: nothing below claims live data exists.
const WARNINGS_NOT_RUN =
  "No simulation has been run, so no engineering warnings have been checked.";
const WARNINGS_NONE =
  "The backend returned no rule-based warnings. This is not real-world validation.";
const SENSOR_NOTE =
  "Last update: none. Live sensor readings are not implemented.";
const TELEMETRY_NOTE =
  "Live sensor readings and component outputs are not implemented. " +
  "Installed sensors are listed without values, and the output table shows catalog specifications only.";

let catalog = [];
let parts = [];
let selected = null;
let nextId = 1;

let scene, camera, renderer, controls, raycaster, transformControls, selectedOutline;
let assemblyRoot, ambientLight, safetyLight, keyLight, fillLight, rgbLight;
let headlight, headlightTarget;
const auxiliaryLights = [];
const rearLights = [];
let viewportObserver = null;

let driveTimer = null;
let simulatedAcceleration = null;
let simulatedSlopeDegrees = 0;
let currentDriveDirection = null;
let steeringInput = 0;
let steeringAngle = 0;
let driveVelocity = 0;
let driveSpeedScale = 0.5;
let previousFrameTime = 0;
let animationStarted = false;
let trajectoryPlayback = null;

// Transform mode lives here, not in the gizmo, so selecting a part never resets it.
const TOOL_MODES = {
  "move-tool": "translate",
  "rotate-tool": "rotate",
  "scale-tool": "scale"
};
const MODE_LABELS = { translate: "Move", rotate: "Rotate", scale: "Scale" };
let transformMode = "translate";

// Simulation status: idle | running | complete | outdated | error
let simState = "idle";
let simulationVersion = 0;
let componentControlsWired = false;
let keyboardDriveCode = null;

const mats = {
  chassis: new THREE.MeshStandardMaterial({
    color: 0x4d83c6, metalness: 0.4, roughness: 0.5
  }),
  metal: new THREE.MeshStandardMaterial({
    color: 0xc7d5e8, metalness: 0.65, roughness: 0.3
  }),
  wheel: new THREE.MeshStandardMaterial({
    color: 0x202a3b, roughness: 0.85
  }),
  battery: new THREE.MeshStandardMaterial({ color: 0x35b98b }),
  sensor: new THREE.MeshStandardMaterial({ color: 0x56d8ee }),
  highlight: new THREE.MeshStandardMaterial({ color: 0xffc65c })
};

function render() {
  if (!renderer || !scene || !camera) return;
  if (selectedOutline && selected) selectedOutline.setFromObject(selected.group);
  renderer.render(scene, camera);
}

// --------------------------------------------------
// TRANSFORM MODE (Move / Rotate / Scale)
// --------------------------------------------------

function setTransformMode(mode) {
  if (!MODE_LABELS[mode]) return;

  transformMode = mode;

  if (transformControls) {
    transformControls.setMode(mode);

    // showX/showY/showZ apply to every mode, so reset them per mode.
    const yawOnly = ROTATE_Y_ONLY && mode === "rotate";
    transformControls.showX = !yawOnly;
    transformControls.showY = true;
    transformControls.showZ = !yawOnly;
  }

  for (const [id, toolMode] of Object.entries(TOOL_MODES)) {
    const button = $(id);
    if (!button) continue;

    const active = toolMode === mode;
    button.setAttribute("aria-pressed", String(active));
    button.classList.toggle("active", active);
  }

  render();
}

// --------------------------------------------------
// INITIALIZE THE 3D VIEW
// --------------------------------------------------

function snapSelectedPart() {
  if (!selected || !selected.group) return;

  const moving = selected.group;

  let nearest = null;
  let nearestDistance = SNAP_DISTANCE;

  for (const part of parts) {
    if (
      part.instanceId === selected.instanceId ||
      !part.group
    ) {
      continue;
    }

    const distance = moving.position.distanceTo(
      part.group.position
    );

    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearest = part;
    }
  }

  if (nearest) {
    moving.position.copy(nearest.group.position);
    if (selected) {
      selected.basePosition = {
        x: moving.position.x,
        y: moving.position.y,
        z: moving.position.z
      };
    }
  }
}

function init() {
  const host = $("viewport");

  if (!host) {
    throw new Error('Missing HTML element: "viewport".');
  }

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b1525);
  assemblyRoot = new THREE.Group();
  assemblyRoot.name = "robot-assembly";
  scene.add(assemblyRoot);

  camera = new THREE.PerspectiveCamera(
    48,
    Math.max(host.clientWidth, 1) / Math.max(host.clientHeight, 1),
    0.1,
    1000
  );

  camera.position.set(5.5, 4.5, 7);
  camera.lookAt(0, 0.5, 0);

  renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: false
  });

  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(
    Math.max(host.clientWidth, 1),
    Math.max(host.clientHeight, 1)
  );
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  host.insertBefore(renderer.domElement, host.firstChild);

  // The host can resize without a window resize (for example at a layout
  // breakpoint), so keep the drawing buffer and camera matched to its box.
  if ("ResizeObserver" in window) {
    viewportObserver = new ResizeObserver(resize);
    viewportObserver.observe(host);
  }
  resize();

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.target.set(0, 0.5, 0);
  controls.maxPolarAngle = Math.PI * 0.48;
  controls.minDistance = 2;
  controls.maxDistance = 35;
  controls.saveState();

  transformControls = new TransformControls(camera, renderer.domElement);
  scene.add(transformControls.getHelper());
  selectedOutline = new THREE.BoxHelper(assemblyRoot, 0xffc65c);
  selectedOutline.visible = false;
  scene.add(selectedOutline);

  // Mode buttons only change the mode; selecting a part keeps it.
  for (const [id, mode] of Object.entries(TOOL_MODES)) {
    on(id, "click", () => setTransformMode(mode));
  }
  setTransformMode(transformMode);

  transformControls.addEventListener("dragging-changed", event => {
    controls.enabled = !event.value;
  });

  transformControls.addEventListener("objectChange", () => {
    if (!selected) return;

    // Snapping moves the part onto a neighbour, so it only makes sense
    // while moving. Rotating or scaling must not change the position.
    if (transformMode === "translate") {
      snapSelectedPart();
    } else if (transformMode === "scale") {
      selected.group.scale.clampScalar(SCALE_MIN, SCALE_MAX);
    }

    if (selected) {
      selected.basePosition = {
        x: selected.group.position.x,
        y: selected.group.position.y,
        z: selected.group.position.z
      };
    }

    invalidateSimulation();
  });

  ambientLight = new THREE.HemisphereLight(0xc4dcff, 0x263044, 1.4);
  ambientLight.name = "lab-ambient-light";
  scene.add(ambientLight);

  safetyLight = new THREE.HemisphereLight(0x8ca4c4, 0x263044, 0.18);
  safetyLight.name = "lab-safety-fill-light";
  scene.add(safetyLight);

  keyLight = new THREE.DirectionalLight(0xffffff, 1.8);
  keyLight.name = "lab-key-light";
  keyLight.position.set(4, 8, 5);
  keyLight.castShadow = true;
  scene.add(keyLight);

  fillLight = new THREE.DirectionalLight(0x7baaff, 0.8);
  fillLight.name = "lab-fill-light";
  fillLight.position.set(-5, 4, -4);
  scene.add(fillLight);

  rgbLight = new THREE.PointLight(0x45d6e8, 1.2, 14);
  rgbLight.name = "lab-rgb-light";
  rgbLight.position.set(0, 3, 2);
  scene.add(rgbLight);

  headlight = new THREE.SpotLight(0xffffff, 8, 12, Math.PI / 7, 0.45, 1.5);
  headlight.name = "robot-headlight";
  headlight.position.set(0, 1.05, -0.95);
  headlight.visible = false;
  headlightTarget = new THREE.Object3D();
  headlightTarget.position.set(0, 0.65, -8);
  assemblyRoot.add(headlight, headlightTarget);
  headlight.target = headlightTarget;

  for (const x of [-0.38, 0.38]) {
    const light = new THREE.SpotLight(0x9bdcff, 4, 10, Math.PI / 8, 0.55, 1.5);
    const target = new THREE.Object3D();
    light.position.set(x, 0.85, -0.75);
    target.position.set(x, 0.35, -8);
    light.target = target;
    light.visible = false;
    assemblyRoot.add(light, target);
    auxiliaryLights.push(light);
  }

  for (const x of [-0.48, 0.48]) {
    const light = new THREE.PointLight(0xff3d52, 1.2, 4, 2);
    light.position.set(x, 0.56, 0.9);
    light.visible = false;
    assemblyRoot.add(light);
    rearLights.push(light);
  }

  const grid = new THREE.GridHelper(
    20, 40, 0x315075, 0x20324a
  );
  grid.position.y = -0.03;
  scene.add(grid);

  scene.add(new THREE.AxesHelper(1));

  raycaster = new THREE.Raycaster();

  renderer.domElement.addEventListener("pointerdown", pick);
  if (!viewportObserver) window.addEventListener("resize", resize);
  setupLightingControls();
  setupComponentControls();

  animationStarted = true;
  animate();

  console.log("BLUEPRINT 3D initialized.");
  console.log("Initial scene objects:", scene.children.length);
}

function resize() {
  if (!camera || !renderer) return;

  const host = $("viewport");
  if (!host) return;

  const { width, height } = host.getBoundingClientRect();
  if (width <= 0 || height <= 0) return;

  camera.aspect = width / height;
  camera.updateProjectionMatrix();

  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(width, height);
}

function setupPanelResizing() {
  const root = document.documentElement;
  const panels = {
    library: {
      property: "--library-width",
      storageKey: "blueprint_library_width",
      defaultWidth: 270,
      min: 220,
      max: 400
    },
    properties: {
      property: "--properties-width",
      storageKey: "blueprint_properties_width",
      defaultWidth: 280,
      min: 240,
      max: 400
    }
  };

  function applyWidth(name, value, persist = true) {
    const config = panels[name];
    if (!config) return;

    const width = THREE.MathUtils.clamp(value, config.min, config.max);
    root.style.setProperty(config.property, `${width}px`);

    for (const handle of document.querySelectorAll(
      `[data-resize-panel="${name}"]`
    )) {
      handle.setAttribute("aria-valuenow", String(Math.round(width)));
    }

    if (!persist) return;
    try {
      localStorage.setItem(config.storageKey, String(Math.round(width)));
    } catch (error) {
      console.warn(`Could not save ${name} panel width:`, error);
    }
  }

  for (const [name, config] of Object.entries(panels)) {
    let width = config.defaultWidth;
    try {
      const saved = Number(localStorage.getItem(config.storageKey));
      if (Number.isFinite(saved) && saved > 0) width = saved;
    } catch (error) {
      console.warn(`Could not restore ${name} panel width:`, error);
    }
    applyWidth(name, width, false);
  }

  document.querySelectorAll("[data-resize-panel]").forEach(handle => {
    const name = handle.dataset.resizePanel;
    const config = panels[name];
    if (!config) return;

    let drag = null;
    const finish = event => {
      if (!drag || (event && event.pointerId !== drag.pointerId)) return;
      drag = null;
      document.body.classList.remove("resizing-panels");
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", finish);
      document.removeEventListener("pointercancel", finish);
    };
    const move = event => {
      if (!drag || event.pointerId !== drag.pointerId) return;
      const direction = name === "library" ? 1 : -1;
      applyWidth(name, drag.width + (event.clientX - drag.x) * direction);
    };

    handle.addEventListener("pointerdown", event => {
      if (event.button !== 0 || window.matchMedia("(max-width: 1100px)").matches) {
        return;
      }

      event.preventDefault();
      const current = Number.parseFloat(
        getComputedStyle(root).getPropertyValue(config.property)
      );
      drag = {
        pointerId: event.pointerId,
        x: event.clientX,
        width: Number.isFinite(current) ? current : config.defaultWidth
      };
      document.body.classList.add("resizing-panels");
      document.addEventListener("pointermove", move);
      document.addEventListener("pointerup", finish);
      document.addEventListener("pointercancel", finish);
    });

    handle.addEventListener("dblclick", () => {
      applyWidth(name, config.defaultWidth);
    });

    handle.addEventListener("keydown", event => {
      if (event.key === "Home") {
        event.preventDefault();
        applyWidth(name, config.defaultWidth);
        return;
      }

      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const current = Number.parseFloat(
        getComputedStyle(root).getPropertyValue(config.property)
      );
      const direction = name === "library" ? 1 : -1;
      const delta = event.key === "ArrowRight" ? direction : -direction;
      applyWidth(name, (Number.isFinite(current) ? current : config.defaultWidth) +
        delta * (event.shiftKey ? 30 : 10));
    });
  });
}

function animate() {
  if (!animationStarted || !controls || !renderer) return;

  requestAnimationFrame(animate);

  const now = performance.now();
  const delta = previousFrameTime
    ? Math.min((now - previousFrameTime) / 1000, 0.05)
    : 0;
  previousFrameTime = now;
  controls.update();
  updateActuators(delta);
  if (selectedOutline && selected) selectedOutline.setFromObject(selected.group);
  renderer.render(scene, camera);
}

// Update real Three.js light objects; dark mode changes illumination and the
// scene background rather than applying a CSS filter to the canvas.
function syncLighting() {
  const enabled = $("lights-enabled")?.checked ?? true;
  const darkMode = $("dark-mode")?.checked ?? false;
  const dimmer = darkMode ? 0.4 : 1;
  const color = $("rgb-color")?.value || "#45d6e8";
  const brightness = Number($("rgb-brightness")?.value ?? 1.2);
  const beamRange = Number($("headlight-range")?.value ?? 12);
  const beamAngle = Number($("headlight-angle")?.value ?? 16);
  const beamType = $("headlight-beam-type")?.value || "low";
  const headlightEnabled = $("headlight-enabled")?.checked ?? false;
  const auxiliaryEnabled = $("auxiliary-light-enabled")?.checked ?? false;
  const rearEnabled = $("rear-light-enabled")?.checked ?? false;

  if (ambientLight) {
    ambientLight.intensity = 1.4 * dimmer;
    ambientLight.visible = enabled;
  }
  if (safetyLight) safetyLight.intensity = darkMode ? 0.1 : 0.18;
  if (keyLight) {
    keyLight.intensity = 1.8 * dimmer;
    keyLight.visible = enabled;
  }
  if (fillLight) {
    fillLight.intensity = 0.8 * dimmer;
    fillLight.visible = enabled;
  }
  if (rgbLight) {
    rgbLight.color.set(color);
    rgbLight.intensity = brightness * dimmer;
    rgbLight.visible = enabled;
  }
  if (headlight) {
    headlight.color.set(color);
    const beamGain = beamType === "high" ? 11 : beamType === "fog" ? 4 : 8;
    headlight.intensity = brightness * beamGain * dimmer;
    headlight.distance = beamRange;
    headlight.visible = headlightEnabled;
    headlight.angle = THREE.MathUtils.degToRad(beamAngle / 2);
    headlight.penumbra = beamType === "fog" ? 0.92 : 0.38;
  }
  if (headlightTarget) {
    headlightTarget.position.set(
      0,
      beamType === "high" ? 0.8 : beamType === "fog" ? 0.35 : 0.15,
      -0.95 - beamRange
    );
  }
  for (const light of auxiliaryLights) {
    light.color.set(color);
    light.intensity = brightness * 4 * dimmer;
    light.distance = Math.min(beamRange, 12);
    light.visible = auxiliaryEnabled;
  }
  for (const light of rearLights) {
    light.intensity = rearEnabled ? 1.2 * dimmer : 0;
    light.visible = rearEnabled;
  }
  if (scene) {
    scene.background.set(darkMode ? 0x02050a : 0x0b1525);
  }

  setText("rgb-brightness-value", brightness.toFixed(2));
  setText("headlight-range-value", `${beamRange.toFixed(0)} m`);
  setText("headlight-angle-value", `${beamAngle.toFixed(0)}°`);
  const themeToggle = $("theme-toggle");
  if (themeToggle) {
    themeToggle.setAttribute("aria-pressed", String(darkMode));
    themeToggle.title = darkMode
      ? "Switch to standard lighting appearance"
      : "Switch to dark simulation appearance";
  }
}

function setupLightingControls() {
  const panel = document.querySelector(".lab-controls");
  if (!panel || panel.dataset.lightingWired) return;
  panel.dataset.lightingWired = "true";

  for (const id of [
    "lights-enabled", "dark-mode", "headlight-enabled", "rgb-color",
    "rgb-brightness", "headlight-range", "headlight-angle",
    "headlight-beam-type", "auxiliary-light-enabled", "rear-light-enabled"
  ]) {
    on(id, "input", syncLighting);
    on(id, "change", syncLighting);
  }

  on("headlight-beam-type", "change", event => {
    const presets = {
      low: { range: 12, angle: 16 },
      high: { range: 24, angle: 24 },
      fog: { range: 10, angle: 50 }
    };
    const preset = presets[event.currentTarget.value];
    if (!preset) return;
    $("headlight-range").value = String(preset.range);
    $("headlight-angle").value = String(preset.angle);
    syncLighting();
  });

  on("theme-toggle", "click", () => {
    const toggle = $("dark-mode");
    if (!toggle) return;
    toggle.checked = !toggle.checked;
    syncLighting();
  });

  panel.querySelectorAll("[data-light-color]").forEach(button => {
    button.addEventListener("click", () => {
      const color = $("rgb-color");
      if (!color) return;
      color.value = button.dataset.lightColor;
      syncLighting();
    });
  });

  on("drive-speed", "input", event => {
    driveSpeedScale = Number(event.currentTarget.value) / 100;
    const value = `${driveSpeedScale.toFixed(2)}×`;
    setText("drive-speed-value", value);
    setText("drive-speed-label", value);
    if (driveSpeedScale <= 0) {
      if (driveTimer) clearInterval(driveTimer);
      driveTimer = null;
      driveVelocity = 0;
      updateWheelSpeedReadouts();
      setText("drive-status", "Robot paused at zero speed.");
    } else if (currentDriveDirection && !driveTimer) {
      driveRobot(currentDriveDirection);
    }
  });

  syncLighting();
}

// --------------------------------------------------
// 3D COMPONENT GEOMETRY
// --------------------------------------------------

function box(group, w, h, d, material, x, y, z) {
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(w, h, d),
    material
  );

  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);

  return mesh;
}

function geometry(part) {
  const group = new THREE.Group();
  group.userData.id = part.instanceId;

  const id = part.componentId;
  const component = catalog.find(item => item.id === id);

  // Shared finishes keep the full catalogue visually consistent.
  const mat = (color, metalness = 0.2, roughness = 0.5) =>
    new THREE.MeshStandardMaterial({ color, metalness, roughness });

  const dark = mat(0x222b38, 0.25, 0.7);
  const rubber = mat(0x171b22, 0.05, 0.92);
  const silver = mats.metal;
  const blue = mats.chassis;
  const green = mats.battery;
  const cyan = mats.sensor;
  const gold = mat(0xdcae48, 0.65, 0.3);
  const pcb = mat(0x176b52, 0.1, 0.65);
  const black = mat(0x101722, 0.15, 0.7);
  const white = mat(0xdde8f5, 0.1, 0.4);

  // Keep the box dimensions explicit before material and position arguments.
  const B = (w, h, d, material, x, y, z, target = group) =>
    box(target, w, h, d, material, x, y, z);

  // CylinderGeometry's default axis is Y.
  const C = (
    radius, length, material, x, y, z, axis = "y", segments = 24,
    target = group
  ) => {
    const mesh = new THREE.Mesh(
      new THREE.CylinderGeometry(radius, radius, length, segments),
      material
    );

    if (axis === "x") mesh.rotation.z = Math.PI / 2;
    if (axis === "z") mesh.rotation.x = Math.PI / 2;

    mesh.position.set(x, y, z);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    target.add(mesh);
    return mesh;
  };

  const S = (radius, material, x, y, z) => {
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(radius, 16, 12),
      material
    );
    mesh.position.set(x, y, z);
    mesh.castShadow = true;
    group.add(mesh);
    return mesh;
  };

  const frame = (w, h, d, t, material, y) => {
    B(w, t, d, material, 0, y, 0);
    B(t, h, d, material, -w / 2, y + h / 2, 0);
    B(t, h, d, material, w / 2, y + h / 2, 0);
    B(w, h, t, material, 0, y + h / 2, -d / 2);
    B(w, h, t, material, 0, y + h / 2, d / 2);
  };

  switch (id) {
    // 1. Basic DC motor
    case "motor_basic":
      C(0.17, 0.38, silver, 0, 0.7, 0, "z", 32);
      C(0.18, 0.06, dark, 0, 0.7, -0.22, "z");
      C(0.07, 0.24, gold, 0, 0.7, 0.28, "z");
      B(0.3, 0.04, 0.12, dark, 0, 0.51, 0);
      part.shaft = C(0.035, 0.25, silver, 0, 0.7, 0.44, "z");
      break;

    // 2. Basic robot wheel
    case "wheel_basic":
    case "space_rover_wheel": {
      const rover = id === "space_rover_wheel";
      const radius = rover ? 0.4 : 0.34;
      const width = rover ? 0.28 : 0.2;
      const pivot = new THREE.Group();
      pivot.position.y = radius;
      group.add(pivot);
      part.wheelPivot = pivot;
      part.wheelRadius = radius;

      C(radius, width, rubber, 0, 0, 0, "x", 40, pivot);
      C(radius * 0.68, width + 0.02, silver, 0, 0, 0, "x", 32, pivot);
      C(radius * 0.36, width + 0.05, gold, 0, 0, 0, "x", 24, pivot);

      // Tread blocks around the wheel.
      for (let i = 0; i < 16; i++) {
        const a = (i / 16) * Math.PI * 2;
        const tread = B(
          width * 1.12,
          rover ? 0.1 : 0.065,
          rover ? 0.075 : 0.045,
          dark,
          Math.cos(a) * radius,
          Math.sin(a) * radius,
          0,
          pivot
        );
        tread.rotation.z = -a;
      }

      for (let i = 0; i < 6; i++) {
        const a = (i / 6) * Math.PI * 2;
        C(
          0.025, width + 0.055, dark,
          Math.cos(a) * radius * 0.47,
          Math.sin(a) * radius * 0.47,
          0, "x", 10, pivot
        );
      }
      break;
    }

    // 3. 12 V battery pack
    case "battery_basic":
      B(0.64, 0.34, 0.78, green, 0, 0.48, 0);
      B(0.58, 0.04, 0.74, dark, 0, 0.67, 0);
      B(0.42, 0.025, 0.5, white, 0, 0.695, 0);
      C(0.045, 0.07, gold, -0.18, 0.72, -0.2);
      C(0.045, 0.07, silver, 0.18, 0.72, -0.2);
      B(0.26, 0.035, 0.2, dark, 0, 0.25, 0.4);
      break;

    // 4. Robot chassis
    case "chassis_basic":
      B(1.65, 0.16, 2.15, blue, 0, 0.58, 0);
      B(1.42, 0.04, 1.85, silver, 0, 0.68, 0);
      B(0.1, 0.12, 1.95, silver, -0.68, 0.7, 0);
      B(0.1, 0.12, 1.95, silver, 0.68, 0.7, 0);

      for (const x of [-0.65, 0.65]) {
        for (const z of [-0.86, 0.86]) {
          C(0.035, 0.025, gold, x, 0.7, z);
        }
      }
      break;

    // 5. Ultrasonic distance sensor
    case "sensor_basic":
      B(0.3, 0.18, 0.22, pcb, 0, 0.55, 0);
      for (const x of [-0.075, 0.075]) {
        C(0.055, 0.04, silver, x, 0.57, 0.13, "z", 24);
        C(0.037, 0.045, dark, x, 0.57, 0.155, "z", 24);
      }
      B(0.08, 0.025, 0.08, gold, 0, 0.45, -0.1);
      if (Number(component?.range_m) > 0) {
        part.sensorRange = Number(part.sensorRange || component.range_m);
        part.sensorBeam = new THREE.Mesh(
          new THREE.ConeGeometry(0.36, part.sensorRange, 24, 1, true),
          new THREE.MeshBasicMaterial({
            color: 0x45d6e8,
            transparent: true,
            opacity: 0.12,
            depthWrite: false,
            side: THREE.DoubleSide
          })
        );
        part.sensorBeam.name = "sensor-detection-cone";
        part.sensorBeam.rotation.x = -Math.PI / 2;
        part.sensorBeam.position.set(
          0, 0.57, -part.sensorRange / 2
        );
        part.sensorBeam.visible = part.sensorEnabled !== false;
        group.add(part.sensorBeam);
      }
      break;

    // 6. Geared DC motor
    case "motor_geared":
      C(0.14, 0.32, silver, 0, 0.62, -0.08, "z");
      C(0.19, 0.19, gold, 0, 0.62, 0.18, "z", 12);
      C(0.075, 0.22, silver, 0, 0.62, 0.38, "z");
      B(0.32, 0.04, 0.12, dark, 0, 0.43, 0.05);
      part.shaft = C(0.035, 0.12, gold, 0, 0.62, 0.52, "z");
      break;

    // 7. Servo motor
    case "servo_basic":
      B(0.25, 0.17, 0.2, blue, 0, 0.52, 0);
      B(0.2, 0.035, 0.2, dark, 0, 0.62, 0);
      part.servoPivot = new THREE.Group();
      part.servoPivot.position.set(0, 0.69, 0);
      group.add(part.servoPivot);
      C(0.035, 0.09, silver, 0, 0, 0, "y", 24, part.servoPivot);
      B(0.28, 0.025, 0.2, white, 0, 0.06, 0, part.servoPivot);
      C(0.025, 0.04, gold, -0.11, 0.06, 0, "y", 24, part.servoPivot);
      C(0.025, 0.04, gold, 0.11, 0.06, 0, "y", 24, part.servoPivot);
      break;

    // 8. Stepper motor
    case "stepper_basic":
      B(0.38, 0.38, 0.3, silver, 0, 0.55, 0);
      B(0.32, 0.06, 0.03, dark, 0, 0.55, 0.17);
      C(0.055, 0.2, gold, 0, 0.55, 0.3, "z");
      for (const x of [-0.13, 0.13]) {
        for (const z of [-0.1, 0.1]) {
          C(0.025, 0.04, dark, x, 0.75, z);
        }
      }
      break;

    // 9. Temperature sensor
    case "sensor_temperature":
      B(0.2, 0.08, 0.16, pcb, 0, 0.48, 0);
      C(0.035, 0.22, silver, 0, 0.55, 0.12, "z");
      C(0.045, 0.08, gold, 0, 0.55, 0.25, "z");
      B(0.12, 0.035, 0.12, dark, 0, 0.43, 0);
      break;

    // 10. IMU sensor board
    case "sensor_imu":
      B(0.28, 0.045, 0.28, pcb, 0, 0.48, 0);
      B(0.11, 0.045, 0.11, black, 0, 0.53, 0);
      for (const x of [-0.1, 0.1]) {
        for (const z of [-0.1, 0.1]) {
          C(0.018, 0.035, gold, x, 0.52, z);
        }
      }
      B(0.06, 0.025, 0.06, silver, 0, 0.57, 0);
      break;

    // 11. Light sensor
    case "sensor_light":
      B(0.22, 0.06, 0.2, pcb, 0, 0.48, 0);
      C(0.065, 0.055, black, 0, 0.54, 0, "y");
      S(0.045, cyan, 0, 0.58, 0);
      B(0.08, 0.025, 0.08, gold, 0, 0.44, 0.11);
      break;

    // 12. Gear with teeth
    case "gear_basic":
      C(0.23, 0.1, gold, 0, 0.5, 0, "y", 24);
      C(0.09, 0.12, silver, 0, 0.5, 0, "y", 16);
      C(0.045, 0.14, dark, 0, 0.5, 0, "y", 16);

      for (let i = 0; i < 12; i++) {
        const a = (i / 12) * Math.PI * 2;
        const tooth = B(
          0.09, 0.1, 0.075, gold,
          Math.cos(a) * 0.235,
          0.5,
          Math.sin(a) * 0.235
        );
        tooth.rotation.y = -a;
      }
      break;

    // 13. Structural support frame
    case "frame_basic":
      frame(0.9, 0.75, 0.8, 0.07, silver, 0.25);
      B(0.9, 0.07, 0.8, blue, 0, 1.0, 0);
      break;

    // 14. Robot controller board
    case "controller_basic":
      B(0.42, 0.045, 0.52, pcb, 0, 0.48, 0);
      B(0.16, 0.06, 0.16, black, 0, 0.535, 0);
      B(0.11, 0.025, 0.11, silver, 0, 0.58, 0);
      for (const x of [-0.16, 0.16]) {
        B(0.045, 0.06, 0.045, gold, x, 0.53, -0.16);
        B(0.045, 0.06, 0.045, gold, x, 0.53, 0.16);
      }
      for (let i = 0; i < 5; i++) {
        C(0.012, 0.025, gold, -0.15 + i * 0.075, 0.515, 0.25);
      }
      break;

    // 15. Power converter
    case "power_converter":
      B(0.34, 0.08, 0.28, pcb, 0, 0.48, 0);
      C(0.065, 0.07, dark, -0.09, 0.56, 0);
      C(0.065, 0.07, silver, 0.09, 0.56, 0);
      B(0.12, 0.035, 0.08, black, 0, 0.54, -0.08);
      for (const x of [-0.12, 0.12]) {
        C(0.018, 0.05, gold, x, 0.52, 0.16);
      }
      break;

    // 16. Spacecraft solar panel
    case "space_solar_panel":
      B(0.12, 0.08, 0.12, silver, 0, 0.52, 0);
      B(0.58, 0.035, 0.035, dark, -0.43, 0.52, 0);
      B(0.58, 0.035, 0.035, dark, 0.43, 0.52, 0);

      for (const side of [-1, 1]) {
        B(0.48, 0.025, 0.72, blue, side * 0.43, 0.57, 0);
        for (let row = 0; row < 4; row++) {
          for (let col = 0; col < 3; col++) {
            B(
              0.125, 0.012, 0.15,
              mat(0x245ba4, 0.4, 0.25),
              side * 0.43 + (col - 1) * 0.145,
              0.59,
              (row - 1.5) * 0.17
            );
          }
        }
      }
      break;

    // 17. Space communication antenna
    case "space_antenna":
      C(0.035, 0.55, silver, 0, 0.77, 0);
      C(0.25, 0.035, white, 0, 1.05, 0, "y", 32);
      S(0.07, gold, 0, 1.05, 0);
      C(0.035, 0.14, gold, 0, 1.14, 0);
      B(0.28, 0.06, 0.28, dark, 0, 0.47, 0);
      break;

    // 18. Planetary science sensor
    case "space_sensor":
      B(0.36, 0.22, 0.3, silver, 0, 0.58, 0);
      B(0.26, 0.12, 0.3, dark, 0, 0.75, 0);
      C(0.09, 0.07, cyan, 0, 0.82, 0, "y", 32);
      C(0.045, 0.08, gold, -0.12, 0.58, 0.18, "z");
      C(0.045, 0.08, gold, 0.12, 0.58, 0.18, "z");
      break;

    // 19. Spacecraft thruster
    case "space_thruster":
      C(0.17, 0.28, silver, 0, 0.68, 0, "y", 24);
      C(0.11, 0.15, dark, 0, 0.48, 0, "y", 24);
      C(0.075, 0.08, gold, 0, 0.36, 0, "y", 24);
      C(0.045, 0.12, black, 0, 0.26, 0, "y", 24);
      B(0.34, 0.06, 0.08, silver, 0, 0.84, 0);
      break;

    // 20. Satellite payload frame
    case "space_payload_frame":
      frame(1.0, 0.65, 1.0, 0.055, gold, 0.25);
      B(0.46, 0.1, 0.46, silver, 0, 0.95, 0);
      for (const x of [-0.35, 0.35]) {
        for (const z of [-0.35, 0.35]) {
          C(0.035, 0.07, dark, x, 0.98, z);
        }
      }
      break;

    // 22. Mars Rover Body — armored hull, equipment bays and mast.
    case "nasa_mars_rover_body": {
      const body = mat(0x8b7355, 0.35, 0.75);
      const panels = mat(0x6b5335, 0.4, 0.65);
      const mounts = mat(0xa89070, 0.55, 0.5);
      B(1.5, 0.2, 1.2, body, 0, 0.6, 0);
      B(1.3, 0.06, 1.0, panels, 0, 0.72, 0);
      B(0.06, 0.3, 1.2, panels, -0.78, 0.55, 0);
      B(0.06, 0.3, 1.2, panels, 0.78, 0.55, 0);
      B(1.2, 0.18, 0.12, panels, 0, 0.62, -0.66);
      B(0.9, 0.14, 0.1, mounts, 0, 0.62, 0.66);
      for (const side of [-1, 1]) {
        for (const z of [-0.45, 0, 0.45]) {
          B(0.14, 0.06, 0.12, mounts, side * 0.85, 0.48, z);
        }
      }
      C(0.06, 0.22, mounts, 0, 0.86, -0.3);
      B(0.18, 0.06, 0.18, panels, 0, 0.98, -0.3);
      break;
    }

    // 23. Lunar Rover Body — open tubular chassis with an instrument deck.
    case "nasa_lunar_rover_body": {
      const frameMetal = mat(0xb8a88a, 0.55, 0.45);
      const deck = mat(0xd4c5a9, 0.4, 0.6);
      B(0.06, 0.06, 1.2, frameMetal, -0.48, 0.35, 0);
      B(0.06, 0.06, 1.2, frameMetal, 0.48, 0.35, 0);
      for (const z of [-0.45, 0, 0.45]) {
        B(0.96, 0.06, 0.06, frameMetal, 0, 0.35, z);
      }
      for (const x of [-0.48, 0.48]) {
        for (const z of [-0.45, 0.45]) {
          B(0.06, 0.36, 0.06, frameMetal, x, 0.53, z);
        }
      }
      B(0.06, 0.06, 1.0, frameMetal, -0.48, 0.71, 0);
      B(0.06, 0.06, 1.0, frameMetal, 0.48, 0.71, 0);
      B(0.96, 0.06, 0.06, frameMetal, 0, 0.71, -0.45);
      B(0.96, 0.06, 0.06, frameMetal, 0, 0.71, 0.45);
      B(0.72, 0.04, 0.5, deck, 0, 0.58, 0);
      for (const side of [-1, 1]) {
        for (const z of [-0.42, 0.42]) {
          B(0.16, 0.05, 0.1, frameMetal, side * 0.56, 0.32, z);
        }
      }
      break;
    }

    // 24. Six-Wheel Science Rover Body — wide hull and six mounting points.
    case "nasa_six_wheel_rover_body": {
      const body = mat(0x6b7c8e, 0.4, 0.7);
      const panels = mat(0x4a5b6a, 0.45, 0.65);
      const mounts = mat(0x8a9bae, 0.6, 0.4);
      B(1.8, 0.24, 1.4, body, 0, 0.62, 0);
      B(1.6, 0.06, 1.2, panels, 0, 0.76, 0);
      for (const z of [-0.5, 0, 0.5]) {
        B(0.06, 0.24, 0.08, mounts, -0.93, 0.62, z);
        B(0.06, 0.24, 0.08, mounts, 0.93, 0.62, z);
      }
      B(1.4, 0.2, 0.18, panels, 0, 0.64, -0.79);
      B(1.0, 0.28, 0.2, mounts, 0, 0.66, 0.8);
      for (const side of [-1, 1]) {
        for (const z of [-0.55, 0, 0.55]) {
          B(0.18, 0.07, 0.14, mounts, side * 1.0, 0.5, z);
        }
      }
      C(0.055, 0.35, mounts, 0.5, 0.94, -0.5);
      B(0.22, 0.08, 0.16, panels, 0.5, 1.12, -0.5);
      break;
    }

    // 25. Space Exploration Robot Body — modular equipment bays and rails.
    case "nasa_exploration_robot_body": {
      const body = mat(0x7a8b9c, 0.45, 0.6);
      const panels = mat(0x5a6b7c, 0.5, 0.55);
      const deck = mat(0xdde8f5, 0.2, 0.55);
      B(1.6, 0.26, 1.1, body, 0, 0.63, 0);
      B(0.22, 0.36, 0.7, panels, -0.91, 0.68, 0);
      B(0.22, 0.36, 0.7, panels, 0.91, 0.68, 0);
      B(1.3, 0.07, 0.85, deck, 0, 0.77, 0);
      B(0.42, 0.05, 0.38, panels, 0, 0.82, 0.42);
      C(0.04, 0.14, body, -0.16, 0.9, 0.42);
      C(0.04, 0.14, body, 0.16, 0.9, 0.42);
      B(1.2, 0.18, 0.12, panels, 0, 0.65, -0.62);
      for (const side of [-1, 1]) {
        for (const z of [-0.38, 0.38]) {
          B(0.14, 0.06, 0.12, body, side * 1.03, 0.5, z);
        }
      }
      B(0.28, 0.06, 0.28, panels, -0.55, 0.8, 0);
      break;
    }

    // 26. Autonomous Research Rover Body — camera mast and sensor bar.
    case "nasa_research_rover_body": {
      const body = mat(0x8a9b6e, 0.35, 0.65);
      const panels = mat(0x6a7b4e, 0.4, 0.6);
      const metal = mat(0xaabb8e, 0.5, 0.45);
      B(1.1, 0.2, 0.9, body, 0, 0.6, 0);
      B(0.9, 0.05, 0.72, panels, 0, 0.72, 0);
      B(0.05, 0.28, 0.7, panels, -0.58, 0.62, 0);
      B(0.05, 0.28, 0.7, panels, 0.58, 0.62, 0);
      C(0.045, 0.4, metal, 0, 0.9, -0.3);
      B(0.2, 0.07, 0.14, panels, 0, 1.11, -0.3);
      S(0.07, metal, 0, 1.15, -0.3);
      B(0.7, 0.07, 0.08, panels, 0, 0.64, -0.5);
      C(0.03, 0.05, cyan, -0.18, 0.64, -0.55, "z");
      C(0.03, 0.05, cyan, 0.18, 0.64, -0.55, "z");
      for (const side of [-1, 1]) {
        for (const z of [-0.32, 0.32]) {
          B(0.12, 0.05, 0.1, metal, side * 0.65, 0.49, z);
        }
      }
      break;
    }

    // 27. RGB LED unit — a distinct housing with a catalogue-coloured lens.
    case "rgb_led_unit": {
      const lensColor = new THREE.Color(
        part.ledColor ?? component?.default_color_hex ?? 0xff0000
      );
      const ledEnabled = part.ledPowered !== false;
      const ledBrightness = Number(
        part.ledBrightness ?? component?.brightness ?? 1
      );
      const housing = mat(0x2a3040, 0.5, 0.4);
      const lens = new THREE.MeshStandardMaterial({
        color: ledEnabled ? lensColor : 0x222222,
        emissive: ledEnabled ? lensColor : 0x000000,
        emissiveIntensity: ledEnabled ? ledBrightness * 1.5 : 0,
        metalness: 0.1,
        roughness: 0.18
      });
      B(0.28, 0.14, 0.22, housing, 0, 0.52, 0);
      part.ledLens = S(0.07, lens, 0, 0.6, -0.06);
      C(0.1, 0.025, silver, 0, 0.59, -0.06, "z");
      for (const x of [-0.12, -0.04, 0.04, 0.12]) {
        B(0.025, 0.1, 0.16, silver, x, 0.52, 0.13);
      }
      part.componentLight = new THREE.PointLight(
        lensColor,
        ledEnabled ? ledBrightness : 0,
        3
      );
      part.componentLight.position.set(0, 0.62, -0.06);
      part.componentLight.visible = ledEnabled;
      group.add(part.componentLight);
      break;
    }

    // Safe fallback for future or unrecognized component IDs.
    default: {
      const color = new THREE.Color().setHSL(
        (part.instanceId.length * 0.13) % 1, 0.65, 0.55
      );
      const material = mat(color, 0.25, 0.55);
      B(0.4, 0.4, 0.4, material, 0, 0.5, 0);
      B(0.3, 0.04, 0.3, silver, 0, 0.72, 0);
    }
  }

  // Keep raycasting and selection compatible with existing code.
  group.traverse(object => {
    if (object.isMesh) {
      object.userData.id = part.instanceId;
      object.castShadow = true;
      object.receiveShadow = true;
    }
  });

  return group;
}

function spec(id) {
  return catalog.find(component => component.id === id) || {
    id,
    name: id,
    mass_kg: 0,
    max_torque_nm: 0.5,
    radius_m: 0.05
  };
}

function defaultPos(id) {
  // Count within the same group so mixed motor or wheel types do not
  // start on the same slot.
  const sameGroup = WHEEL_IDS.includes(id) ? isWheelPart
    : MOTOR_IDS.includes(id) ? isMotorPart
    : part => part.componentId === id;
  const n = parts.filter(sameGroup).length;

  // Main chassis stays at the center.
  if (id === "chassis_basic") {
    return { x: 0, y: 0, z: 0 };
  }

  // Rover bodies are chassis-sized models and belong at the assembly origin.
  if (id.startsWith("nasa_") && id.endsWith("_body")) {
    return { x: 0, y: 0, z: 0 };
  }

  // Place multiple LED units at separate mounting points.
  if (id === "rgb_led_unit") {
    const positions = [
      { x: 0.55, y: 0.55, z: -0.5 },
      { x: -0.55, y: 0.55, z: -0.5 },
      { x: 0.55, y: 0.55, z: 0.5 },
      { x: -0.55, y: 0.55, z: 0.5 }
    ];
    return positions[n % positions.length];
  }

  // Four wheels: two on each side.
  if (id === "wheel_basic" || id === "space_rover_wheel") {
    const positions = [
      { x: -0.98, y: 0, z: -0.68 },
      { x:  0.98, y: 0, z: -0.68 },
      { x: -0.98, y: 0, z:  0.68 },
      { x:  0.98, y: 0, z:  0.68 }
    ];
    return positions[n % positions.length];
  }

  // Motors positioned close to the wheels.
  if (id === "motor_basic" || id === "motor_geared") {
    const positions = [
      { x: -0.48, y: 0.12, z: -0.55 },
      { x:  0.48, y: 0.12, z: -0.55 },
      { x: -0.48, y: 0.12, z:  0.55 },
      { x:  0.48, y: 0.12, z:  0.55 }
    ];
    return positions[n % positions.length];
  }

  // Power system.
  if (id === "battery_basic") {
    return { x: 0, y: 0.18, z: 0 };
  }

  if (id === "power_converter") {
    return { x: 0.48, y: 0.18, z: 0 };
  }

  // Control electronics.
  if (id === "controller_basic") {
    return { x: -0.35, y: 0.18, z: 0 };
  }

  // Sensors.
  if (id === "sensor_basic" || id === "space_sensor") {
    return { x: 0, y: 0.18, z: -0.95 };
  }

  if (id === "sensor_imu") {
    return { x: 0, y: 0.18, z: 0.35 };
  }

  if (id === "sensor_temperature") {
    return { x: -0.55, y: 0.18, z: 0.35 };
  }

  if (id === "sensor_light") {
    return { x: 0.55, y: 0.18, z: 0.35 };
  }

  // Additional mechanical parts.
  if (id === "servo_basic") {
    return { x: 0, y: 0.2, z: 0.5 };
  }

  if (id === "stepper_basic") {
    return { x: 0.65, y: 0.18, z: 0.5 };
  }

  if (id === "gear_basic") {
    return { x: -0.65, y: 0.18, z: 0.5 };
  }

  if (id === "frame_basic") {
    return { x: 0, y: 0.3, z: 0 };
  }

  // Spacecraft components.
  if (id === "space_solar_panel") {
    return { x: 1.25, y: 0.35, z: 0 };
  }

  if (id === "space_antenna") {
    return { x: 0, y: 0.5, z: 0.65 };
  }

  if (id === "space_thruster") {
    return { x: 0, y: 0.15, z: 0.9 };
  }

  if (id === "space_payload_frame") {
    return { x: 0, y: 0.25, z: 0 };
  }

  // Fallback for unknown components.
  return { x: 0, y: 0, z: 0 };
}

// --------------------------------------------------
// SIMULATION STATUS AND WARNINGS (UI helpers)
// --------------------------------------------------

function setSimStatus(state, detail = "", elapsedMs) {
  simState = state;

  const labels = {
    idle: "Not run",
    running: "Running…",
    complete: "Complete",
    outdated: "Outdated",
    error: "Error"
  };

  const box = $("sim-status");
  if (box) {
    box.dataset.state = state;
    box.setAttribute("aria-busy", String(state === "running"));
  }

  setText("sim-state", labels[state] || state);

  // undefined = leave unchanged, null = reset, number = API request time.
  if (elapsedMs !== undefined) {
    setText(
      "sim-time",
      elapsedMs === null
        ? "—"
        : Math.round(elapsedMs) + " ms (API request)"
    );
  }

  setText("sim-detail", detail);
}

function setWarnings(items, emptyText) {
  const list = $("warning-list");
  const empty = $("warnings-empty");

  if (list) {
    list.replaceChildren();

    for (const item of items) {
      const li = document.createElement("li");
      li.textContent = item;
      list.append(li);
    }
  }

  setText("warning-count", String(items.length));

  if (empty) {
    empty.hidden = items.length > 0;
    if (emptyText) empty.textContent = emptyText;
  }
}

function messageText(item) {
  if (typeof item === "string") return item;
  if (item && typeof item.message === "string") return item.message;
  if (item == null) return "";
  return String(JSON.stringify(item));
}

// --------------------------------------------------
// SENSOR LIST AND COMPONENT OUTPUT TABLE
// No live values exist in this code. These only list what is installed
// and the catalog specifications returned by /api/components.
// --------------------------------------------------

function setField(row, name, text) {
  const el = row.querySelector(`[data-field="${name}"]`);
  if (el) el.textContent = text;
}

function isSensorPart(part) {
  const component = catalog.find(item => item.id === part.componentId);

  return (
    component?.category === "sensor" ||
    /^sensor_|_sensor$/.test(part.componentId)
  );
}

function renderSensors() {
  const list = $("sensor-list");
  const template = $("sensor-row-template");
  const sensors = parts.filter(isSensorPart);

  if (list) {
    list.replaceChildren();

    for (const part of sensors) {
      let row;

      if (template?.content?.firstElementChild) {
        row = template.content.firstElementChild.cloneNode(true);
      } else {
        row = document.createElement("li");
        for (const field of ["name", "value", "unit"]) {
          const span = document.createElement("span");
          span.dataset.field = field;
          row.append(span, " ");
        }
      }

      setField(row, "name", `${part.name} (${part.instanceId})`);
      setField(row, "value", "—");
      setField(row, "unit", "no live reading");
      list.append(row);
    }
  }

  const empty = $("sensor-empty");
  if (empty) {
    empty.hidden = sensors.length > 0;
    empty.textContent = "No sensor components in the assembly.";
  }

  setText("sensor-updated", SENSOR_NOTE);
}

function renderComponentOutputs() {
  const body = $("component-output-body");
  if (!body) return;

  const emptyRow = $("component-output-empty");
  const template = $("output-row-template");

  body.querySelectorAll("tr:not(#component-output-empty)")
    .forEach(row => row.remove());

  let rowCount = 0;

  for (const part of parts) {
    const component = catalog.find(item => item.id === part.componentId);
    if (!component) continue;

    const specs = [
      ["Rated max torque (spec)", component.max_torque_nm, "N·m"],
      ["Radius (spec)", component.radius_m, "m"]
    ];

    for (const [label, raw, unit] of specs) {
      const value = Number(raw);
      if (raw == null || !Number.isFinite(value) || value <= 0) continue;

      let row;

      if (template?.content?.firstElementChild) {
        row = template.content.firstElementChild.cloneNode(true);
      } else {
        row = document.createElement("tr");
        for (const field of ["component", "output", "value", "status"]) {
          const cell = document.createElement("td");
          cell.dataset.field = field;
          row.append(cell);
        }
      }

      setField(row, "component", `${part.name} (${part.instanceId})`);
      setField(row, "output", label);
      setField(row, "value", `${+value.toFixed(3)} ${unit}`);
      setField(row, "status", "Catalog spec, not a live output");
      body.append(row);
      rowCount++;
    }
  }

  if (emptyRow) {
    emptyRow.hidden = rowCount > 0;

    const cell = emptyRow.firstElementChild;
    if (cell) {
      cell.textContent =
        "No component specifications to list. Live component outputs are not implemented.";
    }
  }
}

// --------------------------------------------------
// ADD, SELECT, MOVE AND REMOVE COMPONENTS
// --------------------------------------------------

function invalidateSimulation() {
  simulationVersion++;
  simulatedAcceleration = null;
  stopTrajectoryPlayback(true);

  const wasDriving = driveTimer !== null;
  stopRobot();

  if (wasDriving) {
    setText(
      "drive-status",
      "Robot stopped: the scene changed. Run the simulation again."
    );
  }

  if (simState === "complete") {
    setSimStatus(
      "outdated",
      "The scene changed after the last run. Results shown are from that earlier run."
    );
  } else if (simState === "running") {
    setSimStatus(
      "outdated",
      "The scene changed while the simulation was running. The response was discarded."
    );

    setText(
      "result-message",
      "Simulation discarded because the scene changed. Run it again."
    );
  }
}

function add(id, position) {
  if (!scene) return;

  if (!catalog.some(component => component.id === id)) {
    console.warn("Component not found in catalogue:", id);
    return;
  }

  invalidateSimulation();

  const component = spec(id);

  const part = {
    instanceId: "part-" + nextId++,
    componentId: id,
    name: component.name || id,
    mass: Number(component.mass_kg) || 0,
    powered: true,
    rpm: Number(component.no_load_rpm) || undefined,
    ledColor: component.default_color_hex
      ? Number.parseInt(component.default_color_hex.slice(1), 16)
      : undefined,
    ledBrightness: Number(component.brightness) || undefined,
    ledPowered: component.powered !== false,
    sensorEnabled: true,
    sensorRange: Number(component.range_m) || undefined
  };

  part.group = geometry(part);

  const pos = position || defaultPos(id);
  part.group.position.set(pos.x, pos.y, pos.z);
  part.basePosition = { x: pos.x, y: pos.y, z: pos.z };
  part.isFrontWheel = isWheelPart(part) && pos.z < 0;
  if (
    isMotorPart(part) ||
    component.category === "actuator" ||
    component.category === "power" ||
    component.category === "sensor"
  ) {
    const indicatorMaterial = new THREE.MeshStandardMaterial({
      color: 0x45d6a0,
      emissive: 0x45d6a0,
      emissiveIntensity: 0.8,
      roughness: 0.3
    });
    part.powerIndicator = new THREE.Mesh(
      new THREE.SphereGeometry(0.035, 12, 8),
      indicatorMaterial
    );
    part.powerIndicator.name = "component-power-indicator";
    part.powerIndicator.position.set(0, 0.82, 0);
    part.powerIndicator.userData.id = part.instanceId;
    part.group.add(part.powerIndicator);
  }

  assemblyRoot.add(part.group);
  parts.push(part);

  select(part.instanceId);
  update();
}

function pick(event) {
  if (!renderer || !raycaster || !camera || !transformControls) return;

  // Only the main button selects; right/middle drags are orbit and pan.
  if (event.button !== 0) return;

  // Ignore clicks that are part of transform-gizmo dragging.
  if (transformControls.dragging) return;

  const rect = renderer.domElement.getBoundingClientRect();

  const pointer = new THREE.Vector2(
    ((event.clientX - rect.left) / rect.width) * 2 - 1,
    -((event.clientY - rect.top) / rect.height) * 2 + 1
  );

  raycaster.setFromCamera(pointer, camera);

  const hit = raycaster.intersectObjects(
    parts.map(part => part.group),
    true
  )[0];

  if (hit) {
    let object = hit.object;
    while (object && !object.userData.id) object = object.parent;
    if (object?.userData.id) select(object.userData.id);
  }
}

function select(id) {
  selected = parts.find(part => part.instanceId === id) || null;

  setHidden("empty", !!selected);
  setHidden("inspector", !selected);
  renderSelectedDetails();

  if (transformControls) {
    if (selected) {
      transformControls.attach(selected.group);

      // Re-apply the chosen mode so selecting a part never changes it.
      setTransformMode(transformMode);
    } else {
      transformControls.detach();
    }
  }

  if (selectedOutline) selectedOutline.visible = !!selected;
  renderComponentControls();
  render();
}

function renderSelectedDetails() {
  const preview = $("selected-preview");
  const name = $("selected-name");
  const category = $("selected-category");
  const specs = $("selected-specs");
  if (!selected || !preview || !name || !category || !specs) return;

  const component = spec(selected.componentId);
  const type = component.category || "other";
  preview.className = `selected-preview category-${type}`;
  preview.textContent = categoryIcons[type] || "◈";
  name.textContent = selected.name;
  category.textContent = categoryLabels[type] ||
    librarySectionLabels[librarySectionFor(component)] || "Component";
  specs.replaceChildren();

  const voltage = component.voltage_v ?? component.rated_voltage_v;
  const torque = component.max_torque_nm ?? component.stall_torque_nm;
  const details = [
    ["Mass", component.mass_kg, "kg"],
    ["Voltage", voltage, "V"],
    ["Torque", torque, "N·m"],
    ["Speed", component.no_load_rpm, "RPM"],
    ["Range", component.range_m, "m"],
    ["Radius", component.radius_m, "m"]
  ];

  for (const [label, rawValue, unit] of details) {
    const value = Number(rawValue);
    if (rawValue == null || !Number.isFinite(value) || value <= 0) continue;
    const item = document.createElement("span");
    item.textContent = `${label} ${Number(value.toFixed(2))} ${unit}`;
    specs.append(item);
  }
}

function countParts(test) {
  return parts.filter(test).length;
}

function update() {
  setText("part-count", `${parts.length} parts`);

  setText(
    "mass",
    parts.reduce((sum, part) => sum + part.mass, 0).toFixed(2) + " kg"
  );

  // Same groups the simulation and driving code use.
  setText("motors", String(countParts(isMotorPart)));
  setText("wheels", String(countParts(isWheelPart)));

  renderSensors();
  renderComponentOutputs();
  renderComponentControls();
}

function addControlField(container, labelText, part, key, options = {}) {
  const label = document.createElement("label");
  label.className = options.checkbox ? "component-toggle" : "range-control";
  label.append(document.createTextNode(labelText));

  if (options.checkbox) {
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = options.checked;
    input.dataset.partId = part.instanceId;
    input.dataset.partControl = key;
    label.prepend(input);
  } else {
    const value = document.createElement("output");
    value.textContent = options.valueText || "";
    label.append(" ", value);
    const input = document.createElement("input");
    input.type = options.type || "range";
    input.min = String(options.min);
    input.max = String(options.max);
    input.step = String(options.step);
    input.value = String(options.value);
    input.dataset.partId = part.instanceId;
    input.dataset.partControl = key;
    label.append(input);
  }

  container.append(label);
}

function renderComponentControls() {
  const host = $("component-controls");
  const empty = $("component-controls-empty");
  const picker = $("installed-part-select");
  const removeButton = $("remove-selected");
  const duplicateButton = $("duplicate-selected");
  if (!host || !picker) return;

  picker.replaceChildren(new Option("Select an installed component", ""));
  for (const part of parts) {
    picker.add(new Option(`${part.name} · ${part.instanceId}`, part.instanceId));
  }
  picker.value = selected?.instanceId || "";

  host.replaceChildren();
  host.hidden = !selected;
  if (removeButton) removeButton.hidden = !selected;
  if (duplicateButton) duplicateButton.hidden = !selected;
  if (empty) {
    empty.hidden = !!selected;
    empty.textContent = parts.length
      ? "Select an installed component to see its supported controls."
      : "Add a component, then select it to see its supported controls.";
  }
  if (!selected) return;

  const part = selected;
  const component = spec(part.componentId);
  const controls = host;
  const torque = Number(component.max_torque_nm ?? component.stall_torque_nm);

  if (isMotorPart(part) || component.category === "actuator") {
    addControlField(controls, "Motor power", part, "powered", {
      checkbox: true,
      checked: part.powered !== false
    });
    if (Number.isFinite(torque) && torque > 0) {
      const info = document.createElement("span");
      info.className = "component-spec";
      info.textContent = `Torque: ${torque} N·m (catalogue specification)`;
      controls.append(info);
    }
    const maxRpm = Number(component.no_load_rpm);
    if (Number.isFinite(maxRpm) && maxRpm > 0) {
      addControlField(controls, "Motor speed", part, "rpm", {
        min: 0,
        max: maxRpm,
        step: 1,
        value: part.rpm ?? maxRpm,
        valueText: `${Math.round(part.rpm ?? maxRpm)} RPM`
      });
    }
    if (part.componentId === "servo_basic") {
      addControlField(controls, "Servo angle", part, "servo-angle", {
        min: 0,
        max: 180,
        step: 1,
        value: part.servoAngle ?? 90,
        valueText: `${Math.round(part.servoAngle ?? 90)}°`
      });
    }
  } else if (isWheelPart(part)) {
    addControlField(controls, "Wheel rotation", part, "wheel-angle", {
      min: 0,
      max: 360,
      step: 1,
      value: part.wheelAngle ?? 0,
      valueText: `${Math.round(part.wheelAngle ?? 0)}°`
    });
    if (part.isFrontWheel) {
      addControlField(controls, "Steering angle", part, "wheel-steering", {
        min: -35,
        max: 35,
        step: 1,
        value: THREE.MathUtils.radToDeg(part.wheelSteering ?? 0),
        valueText: `${Math.round(THREE.MathUtils.radToDeg(part.wheelSteering ?? 0))}°`
      });
    }
    const speed = document.createElement("span");
    speed.className = "component-spec";
    speed.dataset.wheelSpeed = part.instanceId;
    speed.textContent = `Wheel speed: ${formatWheelSpeed(part)} RPM (visual estimate)`;
    controls.append(speed);
  } else if (component.category === "power") {
    const voltage = Number(component.voltage_v);
    if (Number.isFinite(voltage) && voltage > 0) {
      const info = document.createElement("span");
      info.className = "component-spec";
      info.textContent = `Voltage: ${voltage} V (catalogue specification)`;
      controls.append(info);
    }
  } else if (part.componentId === "rgb_led_unit") {
    addControlField(controls, "Light on", part, "led-powered", {
      checkbox: true,
      checked: part.ledPowered !== false
    });
    const colorLabel = document.createElement("label");
    colorLabel.className = "range-control";
    colorLabel.append("LED color");
    const color = document.createElement("input");
    color.type = "color";
    color.value = `#${(part.ledColor ?? 0xff0000).toString(16).padStart(6, "0")}`;
    color.dataset.partId = part.instanceId;
    color.dataset.partControl = "led-color";
    colorLabel.append(color);
    controls.append(colorLabel);
    addControlField(controls, "Brightness", part, "led-brightness", {
      min: 0,
      max: 2,
      step: 0.05,
      value: part.ledBrightness ?? 1,
      valueText: Number(part.ledBrightness ?? 1).toFixed(2)
    });
  } else if (component.category === "sensor") {
    addControlField(controls, "Show sensor detection cone", part, "sensor-enabled", {
      checkbox: true,
      checked: part.sensorEnabled !== false
    });
    if (Number(component.range_m) > 0) {
      addControlField(controls, "Detection cone range", part, "sensor-range", {
        min: 0.25,
        max: component.range_m,
        step: 0.05,
        value: part.sensorRange ?? component.range_m,
        valueText: `${Number(part.sensorRange ?? component.range_m).toFixed(2)} m`
      });
    }
    const note = document.createElement("span");
    note.className = "component-spec";
    note.textContent = "Visualization only; live sensor readings are not simulated.";
    controls.append(note);
  }

  if (!controls.children.length) {
    const info = document.createElement("span");
    info.className = "component-spec";
    info.textContent = "No interactive controls are defined for this catalogue part.";
    controls.append(info);
  }
}

function setPartPowered(part, powered) {
  part.powered = powered;
  if (part.powerIndicator) {
    const color = powered ? 0x45d6a0 : 0x63323d;
    part.powerIndicator.material.color.setHex(color);
    part.powerIndicator.material.emissive.setHex(color);
    part.powerIndicator.material.emissiveIntensity = powered ? 0.8 : 0.05;
  }

  if (isMotorPart(part) && !powered && !parts.some(
    other => isMotorPart(other) && other.powered !== false
  )) {
    stopRobot();
    setText("drive-status", "Robot stopped: all installed motors are off.");
  }
}

function updateLed(part) {
  if (!part.ledLens || !part.componentLight) return;
  const color = new THREE.Color(part.ledColor ?? 0xff0000);
  const enabled = part.ledPowered !== false;
  const brightness = Number(part.ledBrightness ?? 1);
  part.ledLens.material.color.copy(color);
  part.ledLens.material.emissive.copy(color);
  part.ledLens.material.emissiveIntensity = enabled ? brightness * 1.5 : 0;
  part.componentLight.color.copy(color);
  part.componentLight.intensity = enabled ? brightness : 0;
  part.componentLight.visible = enabled;
}

function setSensorRange(part, range) {
  part.sensorRange = range;
  if (!part.sensorBeam) return;
  part.sensorBeam.geometry.dispose();
  part.sensorBeam.geometry = new THREE.ConeGeometry(0.36, range, 24, 1, true);
  part.sensorBeam.position.z = -range / 2;
}

function handleComponentControl(event) {
  const target = event.target;
  const id = target.dataset.partId;
  const key = target.dataset.partControl;
  if (!id || !key || (event.type === "change" &&
      ["range", "color"].includes(target.type))) return;
  const part = parts.find(item => item.instanceId === id);
  if (!part) return;

  const value = target.type === "checkbox" ? target.checked : target.value;
  if (key === "powered") setPartPowered(part, value);
  if (key === "rpm") part.rpm = Number(value);
  if (key === "servo-angle") {
    part.servoAngle = Number(value);
    if (part.servoPivot) {
      part.servoPivot.rotation.y = THREE.MathUtils.degToRad(part.servoAngle - 90);
    }
  }
  if (key === "wheel-angle") {
    part.wheelAngle = Number(value);
    if (part.wheelPivot) {
      part.wheelPivot.rotation.x = THREE.MathUtils.degToRad(part.wheelAngle);
    }
  }
  if (key === "wheel-steering") {
    part.wheelSteering = THREE.MathUtils.degToRad(Number(value));
    if (part.wheelPivot) part.wheelPivot.rotation.y = part.wheelSteering;
    steeringAngle = part.wheelSteering;
    steeringInput = steeringAngle / (Math.PI / 6);
  }
  if (key === "led-powered") part.ledPowered = value;
  if (key === "led-color") part.ledColor = Number.parseInt(value.slice(1), 16);
  if (key === "led-brightness") part.ledBrightness = Number(value);
  if (key.startsWith("led-")) updateLed(part);
  if (key === "sensor-enabled") {
    part.sensorEnabled = value;
    if (part.sensorBeam) part.sensorBeam.visible = value;
    setPartPowered(part, value);
  }
  if (key === "sensor-range") setSensorRange(part, Number(value));

  const output = target.closest("label")?.querySelector("output");
  if (output && target.type === "range") {
    if (key === "rpm") output.textContent = `${Math.round(Number(value))} RPM`;
    else if (key === "sensor-range") output.textContent = `${Number(value).toFixed(2)} m`;
    else if (key === "led-brightness") output.textContent = Number(value).toFixed(2);
    else output.textContent = `${Math.round(Number(value))}°`;
  }
  render();
}

function setupComponentControls() {
  const host = $("component-controls");
  if (!host || componentControlsWired) return;
  componentControlsWired = true;
  host.addEventListener("input", handleComponentControl);
  host.addEventListener("change", handleComponentControl);
  on("installed-part-select", "change", event => {
    select(event.currentTarget.value || null);
  });
}

function updateActuators(delta) {
  if (!(delta > 0)) return;
  for (const part of parts) {
    if (part.shaft && part.powered !== false) {
      const rpm = Number(part.rpm ?? spec(part.componentId).no_load_rpm ?? 0);
      part.shaft.rotation.z += THREE.MathUtils.degToRad(rpm * 6 * delta);
    }
  }
}

function formatWheelSpeed(part) {
  const radius = part.wheelRadius || 0;
  const rpm = radius > 0
    ? driveVelocity / (2 * Math.PI * radius) * 60
    : 0;
  return rpm.toFixed(1);
}

function updateWheelSpeedReadouts() {
  document.querySelectorAll("[data-wheel-speed]").forEach(output => {
    const part = parts.find(item => item.instanceId === output.dataset.wheelSpeed);
    if (part) output.textContent = `Wheel speed: ${formatWheelSpeed(part)} RPM`;
  });
}

// Frees GPU memory. Shared materials in `mats` are kept.
function disposePart(part) {
  const shared = new Set(Object.values(mats));

  part.group.traverse(object => {
    if (!object.isMesh) return;

    object.geometry?.dispose();

    const list = Array.isArray(object.material)
      ? object.material
      : [object.material];

    for (const material of list) {
      if (material && !shared.has(material)) material.dispose();
    }
  });
}

function removeSelected() {
  if (!selected || !scene) return;

  invalidateSimulation();

  const removed = selected;

  select(null);

  assemblyRoot.remove(removed.group);
  disposePart(removed);
  parts = parts.filter(part => part !== removed);

  update();
}

function duplicateSelected() {
  if (!selected || !scene) return;

  const source = selected;
  const sourcePosition = source.group.position.clone();
  const sourceRotation = source.group.rotation.clone();
  const sourceScale = source.group.scale.clone();
  const position = {
    x: sourcePosition.x + 0.65,
    y: sourcePosition.y,
    z: sourcePosition.z + 0.65
  };

  add(source.componentId, position);
  const duplicate = selected;
  if (!duplicate) return;

  duplicate.group.rotation.copy(sourceRotation);
  duplicate.group.scale.copy(sourceScale);
  duplicate.powered = source.powered;
  duplicate.rpm = source.rpm;
  duplicate.ledColor = source.ledColor;
  duplicate.ledBrightness = source.ledBrightness;
  duplicate.ledPowered = source.ledPowered;
  duplicate.sensorEnabled = source.sensorEnabled;
  duplicate.sensorRange = source.sensorRange;
  duplicate.wheelAngle = source.wheelAngle;
  duplicate.wheelSteering = source.wheelSteering;
  duplicate.servoAngle = source.servoAngle;

  setPartPowered(duplicate, duplicate.powered !== false);
  updateLed(duplicate);
  if (duplicate.servoPivot && Number.isFinite(duplicate.servoAngle)) {
    duplicate.servoPivot.rotation.y =
      THREE.MathUtils.degToRad(duplicate.servoAngle - 90);
  }
  if (duplicate.wheelPivot) {
    duplicate.wheelPivot.rotation.x =
      THREE.MathUtils.degToRad(duplicate.wheelAngle || 0);
    duplicate.wheelPivot.rotation.y = duplicate.wheelSteering || 0;
  }
  if (duplicate.sensorBeam) {
    duplicate.sensorBeam.visible = duplicate.sensorEnabled !== false;
    if (Number.isFinite(duplicate.sensorRange)) {
      setSensorRange(duplicate, duplicate.sensorRange);
    }
  }

  select(duplicate.instanceId);
  update();
}

function resetMovement() {
  stopTrajectoryPlayback(true);
  trajectoryPlayback = null;
  stopRobot();
  if (assemblyRoot) {
    assemblyRoot.position.set(0, 0, 0);
    assemblyRoot.rotation.set(0, 0, 0);
  }
  for (const part of parts.filter(isWheelPart)) {
    part.wheelAngle = 0;
    part.wheelSteering = 0;
    if (part.wheelPivot) part.wheelPivot.rotation.set(0, 0, 0);
  }
  updateWheelSpeedReadouts();
  setText("drive-status", "Movement reset; the assembly is at its starting pose.");
  render();
}

function resetScene() {
  if (!scene) return;

  stopTrajectoryPlayback(true);
  trajectoryPlayback = null;
  invalidateSimulation();
  select(null);

  for (const part of parts) {
    assemblyRoot.remove(part.group);
    disposePart(part);
  }

  parts = [];
  nextId = 1;
  simulatedSlopeDegrees = 0;
  assemblyRoot.position.set(0, 0, 0);
  assemblyRoot.rotation.set(0, 0, 0);
  steeringInput = 0;
  steeringAngle = 0;
  driveVelocity = 0;

  update();

  setText("result-message", "Scene reset. Add components and run a simulation.");
  setHidden("result-grid", true);

  const analysis = $("analysis");
  if (analysis) analysis.innerHTML = "";

  setText("drive-status", "Robot stopped");
  setWarnings([], WARNINGS_NOT_RUN);
  setSimStatus("idle", "Scene reset. No simulation has been run.", null);
}

// --------------------------------------------------
// COMPONENT LIBRARY AND DRAG & DROP
// --------------------------------------------------

// Called once at startup. Dragstart is delegated on the list, so cards
// rendered later (after search or filter changes) work without re-binding.
function setupDragDrop() {
  const list = $("component-list");
  const host = $("viewport");

  if (!list || !host) return;

  list.addEventListener("dragstart", event => {
    const card = event.target.closest(".component-card");
    if (!card) return;

    const id = card.dataset.componentId;
    if (!id || !catalog.some(component => component.id === id)) {
      event.preventDefault();
      return;
    }

    event.dataTransfer.setData("text/plain", id);
    event.dataTransfer.effectAllowed = "copy";
  });

  host.addEventListener("dragover", event => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  });

  host.addEventListener("drop", event => {
    event.preventDefault();

    if (!renderer || !raycaster || !camera) return;

    const id = event.dataTransfer.getData("text/plain");
    if (!id || !catalog.some(component => component.id === id)) return;

    const rect = renderer.domElement.getBoundingClientRect();

    const pointer = new THREE.Vector2(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1
    );

    raycaster.setFromCamera(pointer, camera);

    const ground = new THREE.Plane(
      new THREE.Vector3(0, 1, 0), 0
    );

    const point = new THREE.Vector3();

    if (raycaster.ray.intersectPlane(ground, point)) {
      add(id, { x: point.x, y: 0, z: point.z });
    }
  });
}

async function load() {
  const response = await fetch(API + "/api/components");

  if (!response.ok) {
    throw new Error("Components API returned HTTP " + response.status);
  }

  const data = await response.json();
  catalog = asArray(data.components);

  const list = $("component-list");
  if (list) list.innerHTML = "";

  const searchInput = $("component-search");
  const categoryFilter = $("category-filter");
  const typeFilter = $("type-filter");
  const libraryCount = $("library-count");

  function populateCategories() {
    if (!categoryFilter) return;

    const previousCategory = categoryFilter.value || "all";
    const categories = [...new Set(catalog.map(librarySectionFor))]
      .sort((a, b) => Object.keys(librarySectionLabels).indexOf(a) -
        Object.keys(librarySectionLabels).indexOf(b));
    const types = [...new Set(
      catalog.map(component => component.category).filter(Boolean)
    )].sort();

    categoryFilter.innerHTML = '<option value="all">All categories</option>';

    for (const category of categories) {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = librarySectionLabels[category] || category;
      categoryFilter.append(option);
    }

    categoryFilter.value = categories.includes(previousCategory)
      ? previousCategory
      : "all";

    if (typeFilter) {
      const previousType = typeFilter.value || "all";
      typeFilter.replaceChildren(new Option("All component types", "all"));
      for (const type of types) {
        typeFilter.add(new Option(categoryLabels[type] || type, type));
      }
      typeFilter.value = types.includes(previousType) ? previousType : "all";
    }
  }

  function renderComponents() {
    const query = (searchInput?.value || "").trim().toLowerCase();
    const selectedCategory = categoryFilter?.value || "all";
    const selectedType = typeFilter?.value || "all";

    const filtered = catalog.filter(component => {
      const matchesSearch = [
        component.name,
        component.id,
        component.category,
        component.description,
        ...asArray(component.tags)
      ].some(value => String(value || "").toLowerCase().includes(query));

      const matchesCategory =
        selectedCategory === "all" ||
        librarySectionFor(component) === selectedCategory;

      const matchesType =
        selectedType === "all" || component.category === selectedType;

      return matchesSearch && matchesCategory && matchesType;
    });

    filtered.sort((a, b) => {
      return String(a.name || "").localeCompare(String(b.name || ""));
    });

    if (list) {
      list.innerHTML = "";

      if (!filtered.length) {
        const empty = document.createElement("p");
        empty.className = "hint";
        empty.textContent = "No matching components. Try another search or filter.";
        list.append(empty);
      }

      for (const component of filtered) {
        const id = component.id;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "component-card";
        button.dataset.componentId = id;
        button.draggable = true;
        button.title = `Add ${component.name || id} to the assembly`;

        const icon = document.createElement("span");
        icon.className = `component-thumb category-${component.category || "other"}`;
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = categoryIcons[component.category] || "◈";

        const details = document.createElement("span");
        details.className = "component-card-details";
        const name = document.createElement("strong");
        const category = document.createElement("small");
        name.textContent = component.name || id;
        category.textContent =
          categoryLabels[component.category] || component.category || "Component";
        details.append(name, category);

        const addIcon = document.createElement("span");
        addIcon.className = "component-add-icon";
        addIcon.setAttribute("aria-hidden", "true");
        addIcon.textContent = "+";
        button.append(icon, details, addIcon);
        button.addEventListener("click", () => add(id));
        list.append(button);
      }
    }

    if (libraryCount) {
      libraryCount.textContent = filtered.length === catalog.length
        ? `${catalog.length} components`
        : `${filtered.length} of ${catalog.length}`;
    }
  }

  populateCategories();
  renderComponents();

  searchInput?.addEventListener("input", renderComponents);
  categoryFilter?.addEventListener("change", renderComponents);
  typeFilter?.addEventListener("change", renderComponents);
  on("clear-filters", "click", () => {
    if (searchInput) searchInput.value = "";
    if (categoryFilter) categoryFilter.value = "all";
    if (typeFilter) typeFilter.value = "all";
    renderComponents();
  });

  // Import a component selected from Space Library. Storage access can
  // throw (blocked storage), so it must not break startup.
  let pendingId = null;

  try {
    pendingId = localStorage.getItem("blueprint_pending_component");
    if (pendingId) localStorage.removeItem("blueprint_pending_component");
  } catch (error) {
    console.warn("Could not read pending component:", error);
  }

  if (pendingId) {
    if (catalog.some(component => component.id === pendingId)) {
      add(pendingId);
    } else {
      console.warn("Selected library component not found:", pendingId);
    }
  }

  // The catalog is needed for sensor and output rows.
  update();
}

// --------------------------------------------------
// BACKEND HEALTH
// --------------------------------------------------

async function health() {
  const status = $("api-status");

  try {
    const response = await fetch(API + "/health");
    if (!response.ok) throw new Error("Backend unavailable");

    if (status) {
      status.textContent = "Backend connected";
      status.style.color = "#45d6a0";
    }
  } catch {
    if (status) {
      status.textContent = "Backend unavailable";
      status.style.color = "#ff777f";
    }
  }
}

// --------------------------------------------------
// SLOPE INPUT AND PHYSICS SIMULATION
// --------------------------------------------------

function setupSlopeInput() {
  if ($("slope-degrees")) return;

  const simulateButton = $("simulate");
  if (!simulateButton?.parentElement) return;

  const label = document.createElement("label");
  label.htmlFor = "slope-degrees";
  label.textContent = "Slope (degrees) ";

  const input = document.createElement("input");
  input.id = "slope-degrees";
  input.type = "number";
  input.min = "0";
  input.max = "89.99";
  input.step = "1";
  input.value = "0";
  input.title = "Slope angle, from 0 to 89.99 degrees.";

  label.append(input);
  simulateButton.parentElement.insertBefore(label, simulateButton);
}

// Shows "—" instead of "NaN N" when the backend omits a field.
function formatValue(value, unit) {
  const number = Number(value);
  return value == null || !Number.isFinite(number)
    ? "—"
    : number.toFixed(2) + " " + unit;
}

// The request has one torque and one radius field. For several parts this
// sends their average, which equals the old behaviour when all parts share
// one component ID. Missing catalog values fall back to the previous
// defaults, and every fallback or averaging step is reported to the user.
function averageSpec(list, field, fallback, label, unit, notes) {
  const values = [];
  const missing = new Set();

  for (const part of list) {
    const component = catalog.find(item => item.id === part.componentId);
    const raw = component?.[field];
    const number = Number(raw);

    if (raw != null && Number.isFinite(number) && number > 0) {
      values.push(number);
    } else {
      values.push(fallback);
      missing.add(part.componentId);
    }
  }

  if (missing.size) {
    notes.push(
      `No ${label} in the catalog for ${[...missing].join(", ")}; assumed ${fallback} ${unit}.`
    );
  }

  if (new Set(list.map(part => part.componentId)).size > 1) {
    notes.push(`Mixed ${label} types were averaged into one request value.`);
  }

  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

async function simulate() {
  invalidateSimulation();

  const motorParts = parts.filter(
    part => isMotorPart(part) && part.powered !== false
  );
  const wheelParts = parts.filter(isWheelPart);

  if (
    !parts.some(part => part.componentId === "chassis_basic") ||
    motorParts.length === 0 ||
    wheelParts.length === 0
  ) {
    setText(
      "result-message",
      "Add at least one chassis, one motor and one wheel first."
    );
    setSimStatus(
      "idle",
      "Not run: the model needs a chassis, a motor and a wheel.",
      null
    );
    return;
  }

  const mass = parts.reduce((sum, part) => sum + part.mass, 0);

  const slopeInput = $("slope-degrees");
  const slope = slopeInput ? Number(slopeInput.value) : 0;

  if (!Number.isFinite(slope) || slope < 0 || slope >= 90) {
    setText("result-message", "Slope must be between 0 and 89.99 degrees.");
    setSimStatus("idle", "Not run: invalid slope value.", null);
    return;
  }

  const notes = [];

  const body = {
    total_mass_kg: Math.max(mass, 0.01),
    motor_torque_nm: averageSpec(
      motorParts, "max_torque_nm", 0.5, "motor torque", "N·m", notes
    ),
    motor_count: motorParts.length,
    wheel_radius_m: averageSpec(
      wheelParts, "radius_m", 0.05, "wheel radius", "m", notes
    ),
    slope_degrees: slope,
    duration_s: 5.0,
    time_step_s: 0.1,
    initial_velocity_ms: 0.0,
    initial_position_m: 0.0,

    installed_component_ids: parts.map(
      part => part.componentId
    )
  };

  // Responses that arrive after the scene changed are ignored.
  const version = simulationVersion;
  const started = performance.now();

  try {
    setText("result-message", "Running simulation…");
    setSimStatus("running", "Waiting for the backend response…", null);

    const response = await fetch(API + "/api/simulate-motion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });

    const data = await response.json().catch(() => ({}));
    const elapsed = performance.now() - started;

    if (version !== simulationVersion) return;

    if (!response.ok) {
      let detail = "Simulation request failed (HTTP " + response.status + ")";
      if (typeof data.detail === "string") {
        detail = data.detail;
      } else if (Array.isArray(data.detail)) {
        detail = data.detail.map(d => d.msg || JSON.stringify(d)).join("; ");
      } else if (data.detail && typeof data.detail === "object") {
        detail = data.detail.message || JSON.stringify(data.detail);
      }

      throw new Error(detail);
    }

    const analysis = data.engineering_analysis || {};
    const baseSim = data.base_simulation || {};

    simulatedAcceleration = Number(
      baseSim.theoretical_acceleration_ms2 ?? data.final_acceleration_ms2 ?? 0
    );

    simulatedSlopeDegrees = slope;

    setText(
      "result-message",
      data.can_move
        ? "The motion model predicts forward movement."
        : "The motion model predicts the robot cannot move (insufficient net force)."
    );

    setHidden("result-grid", false);

    setText("driving", formatValue(data.driving_force_n, "N"));
    setText("gravity", formatValue(data.gravity_resistance_n, "N"));
    setText("net", formatValue(data.net_force_n, "N"));
    setText(
      "accel",
      (data.top_speed_reached && data.final_acceleration_ms2 === 0 && baseSim.theoretical_acceleration_ms2 != null && baseSim.theoretical_acceleration_ms2 > 0)
        ? `${formatValue(baseSim.theoretical_acceleration_ms2, "m/s²")} (cruising at ${formatValue(data.final_velocity_ms, "m/s")})`
        : formatValue(data.final_acceleration_ms2 ?? baseSim.theoretical_acceleration_ms2, "m/s²")
    );
    setText(
      "final-velocity",
      formatValue(data.final_velocity_ms, "m/s") + (data.final_velocity_kmh != null ? ` (${data.final_velocity_kmh} km/h)` : "")
    );
    setText(
      "distance-traveled",
      formatValue(data.distance_traveled_m, "m")
    );
    setText(
      "wheel-rotations",
      formatValue(data.wheel_rotations, "rev")
    );
    setText(
      "wheel-rpm",
      formatValue(data.final_wheel_rpm, "RPM")
    );

    // Warnings go to the warning list; suggestions stay in #analysis.
    setWarnings(
      asArray(analysis.warnings).map(messageText).filter(Boolean),
      WARNINGS_NONE
    );

    const analysisBox = $("analysis");
    if (analysisBox) {
      analysisBox.innerHTML = "";

      asArray(analysis.suggestions).forEach(message => {
        const div = document.createElement("div");
        div.className = "suggestion";
        div.textContent = "Suggestion: " + messageText(message);
        analysisBox.append(div);
      });
    }

    setSimStatus(
      "complete",
      [
        `Time-based motion simulation complete (${data.duration_s}s, ${data.trajectory ? data.trajectory.length : 0} samples).`,
        ...notes
      ].join(" "),
      elapsed
    );

    // Start 3D physical trajectory playback
    if (data.can_move && Array.isArray(data.trajectory) && data.trajectory.length > 0 && data.distance_traveled_m > 0) {
      startTrajectoryPlayback(data, notes, elapsed);
    } else {
      stopTrajectoryPlayback(true);
      if (!data.can_move || data.distance_traveled_m <= 0) {
        setText(
          "drive-status",
          "Robot stationary: zero displacement modeled (insufficient net force)."
        );
      } else if (!Array.isArray(data.trajectory) || data.trajectory.length === 0) {
        setText(
          "drive-status",
          "Playback unavailable: trajectory data is missing or empty."
        );
        showError("Trajectory playback could not start: invalid trajectory data.");
      }
    }
  } catch (error) {
    if (version !== simulationVersion) return;

    simulatedAcceleration = null;

    setText(
      "result-message",
      "Simulation error: " + error.message +
      ". Check the backend terminal."
    );

    setSimStatus("error", error.message, performance.now() - started);
  }
}

// --------------------------------------------------
// TIME-BASED TRAJECTORY PLAYBACK
// Animates the assembled robot according to physical trajectory coordinates.
// --------------------------------------------------

function interpolateTrajectory(samples, time) {
  if (!samples || samples.length === 0) {
    return { position_m: 0, velocity_ms: 0, acceleration_ms2: 0, time_s: time };
  }
  if (time <= samples[0].time_s) {
    return samples[0];
  }
  const last = samples[samples.length - 1];
  if (time >= last.time_s) {
    return last;
  }

  let low = 0;
  let high = samples.length - 1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (samples[mid].time_s <= time) {
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }

  const idx = Math.max(0, high);
  const s0 = samples[idx];
  const s1 = samples[Math.min(idx + 1, samples.length - 1)];
  const dt = s1.time_s - s0.time_s;
  if (dt <= 1e-6) return s0;

  const alpha = (time - s0.time_s) / dt;
  return {
    time_s: time,
    position_m: s0.position_m + alpha * (s1.position_m - s0.position_m),
    velocity_ms: s0.velocity_ms + alpha * (s1.velocity_ms - s0.velocity_ms),
    acceleration_ms2: s0.acceleration_ms2 + alpha * (s1.acceleration_ms2 - s0.acceleration_ms2)
  };
}

function stopTrajectoryPlayback(resetToOrigin = false) {
  if (trajectoryPlayback) {
    if (trajectoryPlayback.animId) {
      cancelAnimationFrame(trajectoryPlayback.animId);
      trajectoryPlayback.animId = null;
    }
    trajectoryPlayback.active = false;
  }

  if (resetToOrigin) {
    if (assemblyRoot) {
      assemblyRoot.position.set(0, 0, 0);
      assemblyRoot.rotation.set(0, 0, 0);
    }
    for (const part of parts) {
      if (part.basePosition && part.group) {
        part.group.position.set(
          part.basePosition.x,
          part.basePosition.y,
          part.basePosition.z
        );
      }
      if (part.wheelPivot) {
        part.wheelPivot.rotation.x = THREE.MathUtils.degToRad(part.wheelAngle || 0);
        part.wheelPivot.rotation.y = 0;
        part.wheelSteering = 0;
      }
    }
    steeringInput = 0;
    steeringAngle = 0;
    render();
  }
}

function startTrajectoryPlayback(data, notes = [], elapsedApiMs = null) {
  stopRobot();
  stopTrajectoryPlayback(true);

  if (!data || !Array.isArray(data.trajectory) || data.trajectory.length === 0) {
    setText(
      "drive-status",
      "Playback unavailable: trajectory data is missing or empty."
    );
    showError("Trajectory playback could not start: invalid trajectory data.");
    return;
  }

  // Ensure all parts have a recorded basePosition before animating
  for (const part of parts) {
    if (!part.basePosition && part.group) {
      part.basePosition = {
        x: part.group.position.x,
        y: part.group.position.y,
        z: part.group.position.z
      };
    }
    if (part.basePosition && part.group) {
      part.group.position.set(
        part.basePosition.x,
        part.basePosition.y,
        part.basePosition.z
      );
    }
  }
  render();

  const trajectory = data.trajectory;
  const duration = Number(data.duration_s) || trajectory[trajectory.length - 1].time_s || 5.0;
  const totalDisp = Number(data.distance_traveled_m) || 0;

  if (totalDisp <= 0 || !data.can_move) {
    setText(
      "drive-status",
      "Robot stationary: zero displacement modeled (insufficient net force)."
    );
    return;
  }

  const slopeDeg = Number(data.slope_degrees ?? simulatedSlopeDegrees ?? 0);
  const slopeRad = (slopeDeg * Math.PI) / 180;
  const cosSlope = Math.cos(slopeRad);
  const sinSlope = Math.sin(slopeRad);
  const initialPos = Number(data.initial_position_m) || trajectory[0].position_m || 0;

  const currentVersion = simulationVersion;
  const startTime = performance.now();

  trajectoryPlayback = {
    active: true,
    completed: false,
    animId: null,
    data: data,
    duration: duration,
    cosSlope: cosSlope,
    sinSlope: sinSlope,
    initialPos: initialPos
  };

  setText(
    "drive-status",
    `Starting trajectory playback: 0.00s / ${duration.toFixed(2)}s (target: ${totalDisp.toFixed(2)}m)`
  );

  function step() {
    if (currentVersion !== simulationVersion) return;
    if (!trajectoryPlayback || !trajectoryPlayback.active) return;

    const now = performance.now();
    const elapsedSec = (now - startTime) / 1000;
    const simTime = Math.min(elapsedSec, duration);

    const state = interpolateTrajectory(trajectory, simTime);
    const disp = state.position_m - initialPos;

    const deltaZ = -disp * cosSlope;
    const deltaY = disp * sinSlope;

    if (assemblyRoot) {
      assemblyRoot.position.set(0, deltaY, deltaZ);
    }

    render();

    setText(
      "drive-status",
      `Playing trajectory: t=${simTime.toFixed(2)}s / ${duration.toFixed(2)}s | disp=${disp.toFixed(2)}m | v=${state.velocity_ms.toFixed(2)}m/s | a=${state.acceleration_ms2.toFixed(2)}m/s²`
    );

    if (elapsedSec < duration) {
      trajectoryPlayback.animId = requestAnimationFrame(step);
    } else {
      trajectoryPlayback.active = false;
      trajectoryPlayback.completed = true;
      trajectoryPlayback.animId = null;

      setText(
        "drive-status",
        `Trajectory playback completed: traveled ${disp.toFixed(2)}m in ${duration.toFixed(2)}s (final v: ${state.velocity_ms.toFixed(2)}m/s).`
      );
      setSimStatus(
        "complete",
        [
          `Trajectory playback complete (${duration.toFixed(1)}s, ${trajectory.length} samples, ${disp.toFixed(2)}m traveled).`,
          ...notes
        ].join(" "),
        elapsedApiMs
      );
    }
  }

  trajectoryPlayback.animId = requestAnimationFrame(step);
}

// --------------------------------------------------
// MANUAL ROBOT DRIVING
// Visual steering with scaled acceleration for interactive exploration.
// --------------------------------------------------

function stopRobot() {
  if (driveTimer) {
    clearInterval(driveTimer);
    driveTimer = null;
  }

  keyboardDriveCode = null;
  currentDriveDirection = null;
  driveVelocity = 0;
  steeringInput = 0;
  applySteeringAngle(0);
  updateWheelSpeedReadouts();
}

function applySteeringAngle(angle) {
  const wheelbase = 1.36;
  const track = 1.96;
  steeringAngle = THREE.MathUtils.clamp(angle, -Math.PI / 6, Math.PI / 6);

  const radius = Math.abs(steeringAngle) > 1e-4
    ? wheelbase / Math.tan(Math.abs(steeringAngle))
    : Infinity;

  for (const part of parts.filter(isWheelPart)) {
    if (!part.wheelPivot) continue;

    if (!part.isFrontWheel || !Number.isFinite(radius)) {
      part.wheelSteering = 0;
    } else {
      const isInnerWheel = Math.sign(part.group.position.x) ===
        -Math.sign(steeringAngle);
      const offset = (isInnerWheel ? -1 : 1) * track / 2;
      part.wheelSteering = Math.sign(steeringAngle) *
        Math.atan(wheelbase / Math.max(0.1, radius + offset));
    }

    part.wheelPivot.rotation.y = part.wheelSteering;
  }

  for (const input of document.querySelectorAll(
    '[data-part-control="wheel-steering"]'
  )) {
    const part = parts.find(item => item.instanceId === input.dataset.partId);
    if (!part) continue;
    input.value = String(Math.round(
      THREE.MathUtils.radToDeg(part.wheelSteering || 0)
    ));
    const output = input.closest("label")?.querySelector("output");
    if (output) output.textContent = `${input.value}°`;
  }
}

function driveRobot(direction) {
  if (direction === "reset") {
    resetMovement();
    return;
  }

  if (direction === "stop") {
    if (trajectoryPlayback?.active) stopTrajectoryPlayback(false);
    else if (trajectoryPlayback && !trajectoryPlayback.active) {
      stopTrajectoryPlayback(true);
      trajectoryPlayback = null;
    }
    stopRobot();
    setText("drive-status", "Robot stopped; steering returned to centre.");
    return;
  }

  const chassis = parts.find(
    part => part.componentId === "chassis_basic"
  );
  const activeMotors = parts.filter(
    part => isMotorPart(part) && part.powered !== false
  );

  if (
    !chassis ||
    activeMotors.length === 0 ||
    countParts(isWheelPart) < 2
  ) {
    setText(
      "drive-status",
      "Add a chassis, a powered motor and at least two wheels."
    );
    return;
  }

  if (trajectoryPlayback?.active) stopTrajectoryPlayback(false);

  if (direction === "left" || direction === "right") {
    steeringInput = direction === "left" ? 1 : -1;
    applySteeringAngle(steeringInput * Math.PI / 6);
    direction = currentDriveDirection === "backward" ? "backward" : "forward";
  } else if (direction === "forward" || direction === "backward") {
    currentDriveDirection = direction;
  } else {
    return;
  }

  currentDriveDirection = direction;
  const driveSign = direction === "backward" ? -1 : 1;
  const maxSpeed = 2 * driveSpeedScale;
  driveVelocity = driveSign * maxSpeed;

  if (!driveTimer && driveSpeedScale > 0) {
    let lastTick = performance.now();
    driveTimer = setInterval(() => {
      const now = performance.now();
      const delta = Math.min((now - lastTick) / 1000, 0.1);
      lastTick = now;
      const active = parts.some(
        part => isMotorPart(part) && part.powered !== false
      );
      if (!active || driveSpeedScale <= 0) {
        stopRobot();
        setText("drive-status", "Robot stopped: no powered drive motor or speed.");
        return;
      }

      driveVelocity = (currentDriveDirection === "backward" ? -1 : 1) *
        2 * driveSpeedScale;
      if (steeringInput) {
        applySteeringAngle(steeringInput * Math.PI / 6);
      }
      const distance = driveVelocity * delta;
      const forward = new THREE.Vector3(0, 0, -1)
        .applyQuaternion(assemblyRoot.quaternion);
      assemblyRoot.position.addScaledVector(forward, distance);
      assemblyRoot.rotation.y +=
        driveVelocity / 1.36 * Math.tan(steeringAngle) * delta;

      for (const part of parts.filter(isWheelPart)) {
        if (part.wheelPivot && part.wheelRadius) {
          part.wheelPivot.rotation.x += distance / part.wheelRadius;
        }
      }

      updateWheelSpeedReadouts();
    }, 30);
  }

  setText(
    "drive-status",
    `Driving ${direction} at ${Math.round(driveSpeedScale * 100)}% speed` +
    (steeringInput ? ` with ${direction === "backward" ? "reverse " : ""}steering` : "")
  );
}

document.querySelectorAll("[data-drive]").forEach(button => {
  button.addEventListener("click", () => {
    keyboardDriveCode = null;
    driveRobot(button.dataset.drive);
  });
});

document.addEventListener("keydown", event => {
  const activeElement = document.activeElement;
  const activeTag = activeElement?.tagName;
  const textInputTypes = [
    "text", "search", "email", "url", "password", "number", "tel"
  ];

  if (
    activeElement?.isContentEditable ||
    ["TEXTAREA", "SELECT"].includes(activeTag) ||
    (activeTag === "INPUT" && textInputTypes.includes(activeElement.type))
  ) {
    return;
  }

  if (
    activeTag === "INPUT" &&
    ["range", "color"].includes(activeElement.type) &&
    event.key.startsWith("Arrow")
  ) {
    return;
  }
  if (
    event.code === "Space" &&
    (activeTag === "BUTTON" ||
      (activeTag === "INPUT" && ["checkbox", "radio"].includes(activeElement.type)))
  ) {
    return;
  }

  if (!event.key) return;

  if (event.key === "Escape") {
    if (selected) select(null);
    closeMobilePanels();
    return;
  }

  const keys = {
    KeyW: "forward",
    ArrowUp: "forward",
    KeyS: "backward",
    ArrowDown: "backward",
    KeyA: "left",
    ArrowLeft: "left",
    KeyD: "right",
    ArrowRight: "right"
  };

  if (event.code === "Space") {
    event.preventDefault();
    driveRobot("stop");
    return;
  }

  const direction = keys[event.code];

  if (direction) {
    event.preventDefault();
    keyboardDriveCode = event.code;
    driveRobot(direction);
  }
});

document.addEventListener("keyup", event => {
  if (event.code !== keyboardDriveCode) return;
  stopRobot();
  setText("drive-status", "Movement key released; robot stopped.");
});

function closeMobilePanels() {
  const expanded = !window.matchMedia("(max-width: 1100px)").matches;
  for (const [panelId, buttonId] of [
    ["component-library", "toggle-library"],
    ["properties-panel", "toggle-properties"]
  ]) {
    $(panelId)?.classList.remove("mobile-open");
    $(buttonId)?.setAttribute("aria-expanded", String(expanded));
    if (buttonId === "toggle-library") {
      $("library-nav")?.setAttribute("aria-expanded", String(expanded));
    }
  }
}

function setupWorkspaceActions() {
  const isMobile = () => window.matchMedia("(max-width: 1100px)").matches;
  const setDrawer = (panelId, buttonIds) => {
    const panel = $(panelId);
    if (!panel) return;
    if (isMobile()) {
      const opening = !panel.classList.contains("mobile-open");
      if (opening) {
        const otherId = panelId === "component-library"
          ? "properties-panel"
          : "component-library";
        $(otherId)?.classList.remove("mobile-open");
      }
      panel.classList.toggle("mobile-open", opening);
      if (opening) {
        const otherButtonId = panelId === "component-library"
          ? "toggle-properties"
          : "toggle-library";
        $(otherButtonId)?.setAttribute("aria-expanded", "false");
        if (otherButtonId === "toggle-library") {
          $("library-nav")?.setAttribute("aria-expanded", "false");
        }
      }
    } else {
      panel.focus({ preventScroll: true });
    }

    const expanded = isMobile()
      ? panel.classList.contains("mobile-open")
      : true;
    for (const id of buttonIds) {
      $(id)?.setAttribute("aria-expanded", String(expanded));
    }
  };

  const toggleLibrary = () =>
    setDrawer("component-library", ["library-nav", "toggle-library"]);
  const toggleProperties = () =>
    setDrawer("properties-panel", ["toggle-properties"]);

  on("library-nav", "click", toggleLibrary);
  on("toggle-library", "click", toggleLibrary);
  on("toggle-properties", "click", toggleProperties);
  on("toggle-movement", "click", event => {
    const panel = $("movement-panel");
    if (!panel) return;
    const expanded = !panel.classList.toggle("is-collapsed");
    event.currentTarget.setAttribute("aria-expanded", String(expanded));
  });

  on("viewport", "pointerdown", () => {
    if (isMobile()) closeMobilePanels();
  });
  window.addEventListener("resize", () => {
    if (!isMobile()) {
      closeMobilePanels();
      $("library-nav")?.setAttribute("aria-expanded", "true");
      $("toggle-library")?.setAttribute("aria-expanded", "true");
      $("toggle-properties")?.setAttribute("aria-expanded", "true");
    }
  });

  if (!isMobile()) {
    $("library-nav")?.setAttribute("aria-expanded", "true");
  }
}

window.addEventListener("blur", () => {
  if (!keyboardDriveCode) return;
  stopRobot();
  setText("drive-status", "Robot stopped because the window lost focus.");
});

// --------------------------------------------------
// BUTTON HANDLERS
// --------------------------------------------------

on("remove-selected", "click", removeSelected);
on("duplicate-selected", "click", duplicateSelected);
on("simulate", "click", simulate);
on("reset", "click", resetScene);
on("reset-movement", "click", resetMovement);
on("reset-view", "click", () => {
  if (!controls) return;
  controls.reset();
  render();
});
on("screenshot", "click", () => {
  if (!renderer) return;
  renderer.domElement.toBlob(blob => {
    if (!blob) {
      showError("Could not create a screenshot from the WebGL viewport.");
      return;
    }
    const url = URL.createObjectURL(blob);
    const download = document.createElement("a");
    download.href = url;
    download.download = `blueprint-assembly-${new Date().toISOString().replace(/[:.]/g, "-")}.png`;
    download.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }, "image/png");
});
on("fullscreen", "click", async () => {
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    } else {
      const workspace = $("workspace");
      if (!workspace?.requestFullscreen) {
        throw new Error("Fullscreen is not supported by this browser.");
      }
      await workspace.requestFullscreen();
    }
  } catch (error) {
    showError(`Fullscreen is unavailable: ${error.message}`);
  }
});
document.addEventListener("fullscreenchange", () => {
  const button = $("fullscreen");
  if (!button) return;
  const active = document.fullscreenElement === $("workspace");
  button.textContent = active ? "Exit fullscreen" : "Fullscreen";
  button.title = active ? "Exit fullscreen workspace" : "Enter fullscreen workspace";
});

// --------------------------------------------------
// START APPLICATION
// --------------------------------------------------

// Report missing HTML elements once instead of failing later.
const EXPECTED_IDS = [
  "viewport", "component-list", "part-count", "mass", "motors", "wheels",
  "inspector", "empty", "installed-part-select", "component-controls",
  "component-controls-empty", "duplicate-selected", "remove-selected",
  "simulate", "reset", "result-message", "result-grid", "analysis",
  "driving", "gravity", "net", "accel", "drive-status", "drive-speed",
  "drive-speed-value", "drive-speed-label", "api-status", "theme-toggle",
  "movement-panel", "component-library", "properties-panel",
  "headlight-beam-type", "headlight-angle", "auxiliary-light-enabled",
  "rear-light-enabled", "reset-view", "reset-movement", "screenshot", "fullscreen",
  "final-velocity", "distance-traveled", "wheel-rotations", "wheel-rpm",
  "move-tool", "rotate-tool", "scale-tool",
  "sim-status", "sim-state", "sim-time", "sim-detail",
  "sensor-list", "sensor-empty", "sensor-updated",
  "component-output-body", "warning-list", "warning-count", "warnings-empty"
];

const missingIds = EXPECTED_IDS.filter(id => !$(id));
if (missingIds.length) {
  console.warn("builder.html is missing expected elements:", missingIds.join(", "));
}

try {
  setupSlopeInput();
  setupPanelResizing();
  init();
  setupWorkspaceActions();
  setupDragDrop();
  health();

  // Initial honest state for the new panels.
  setSimStatus("idle", "No simulation has been run.", null);
  setWarnings([], WARNINGS_NOT_RUN);
  setText("telemetry-message", TELEMETRY_NOTE);

  update();

  load().catch(error => {
    console.error("Component loading failed:", error);

    setText(
      "component-list",
      "Could not load components: " + error.message
    );

    showError("Check that FastAPI is running and /api/components is available.");
  });
} catch (error) {
  console.error("BLUEPRINT initialization failed:", error);

  showError("3D initialization failed: " + error.message);
  setText("result-message", "3D initialization failed: " + error.message);
}
