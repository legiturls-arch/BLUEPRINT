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

function fixed(value, digits) {
  const text = Number(value).toFixed(digits);
  return /^-0(\.0+)?$/.test(text) ? text.slice(1) : text;
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

let scene, camera, renderer, controls, raycaster, transformControls;

let driveTimer = null;
let simulatedAcceleration = null;
let simulatedSlopeDegrees = 0;
let currentDriveDirection = null;
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

// Text last written into the inspector inputs. Apply only changes fields
// the user actually edited, so rounded display values never overwrite
// precise gizmo results.
let inspectorSnapshot = {};

// Simulation status: idle | running | complete | outdated | error
let simState = "idle";
let simulationVersion = 0;

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
  if (renderer && scene && camera) renderer.render(scene, camera);
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

  setText("transform-mode", "Transform mode: " + MODE_LABELS[mode]);

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

  // replaceChildren() would also delete the #error box that lives inside
  // #viewport, so keep it and put it back after the canvas.
  const errorBox = $("error");
  host.replaceChildren(renderer.domElement);
  if (errorBox) host.append(errorBox);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.target.set(0, 0.5, 0);
  controls.maxPolarAngle = Math.PI * 0.48;
  controls.minDistance = 2;
  controls.maxDistance = 35;

  transformControls = new TransformControls(camera, renderer.domElement);
  scene.add(transformControls.getHelper());

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

    writeInspector();
    invalidateSimulation();
  });

  scene.add(new THREE.HemisphereLight(0xc4dcff, 0x263044, 2));

  const light = new THREE.DirectionalLight(0xffffff, 2.3);
  light.position.set(4, 8, 5);
  light.castShadow = true;
  scene.add(light);

  const fillLight = new THREE.DirectionalLight(0x7baaff, 0.8);
  fillLight.position.set(-5, 4, -4);
  scene.add(fillLight);

  const grid = new THREE.GridHelper(
    20, 40, 0x315075, 0x20324a
  );
  grid.position.y = -0.03;
  scene.add(grid);

  scene.add(new THREE.AxesHelper(1));

  raycaster = new THREE.Raycaster();

  renderer.domElement.addEventListener("pointerdown", pick);
  window.addEventListener("resize", resize);

  animationStarted = true;
  animate();

  console.log("BLUEPRINT 3D initialized.");
  console.log("Initial scene objects:", scene.children.length);
}

function resize() {
  if (!camera || !renderer) return;

  const host = $("viewport");
  if (!host) return;

  const width = Math.max(host.clientWidth, 1);
  const height = Math.max(host.clientHeight, 1);

  camera.aspect = width / height;
  camera.updateProjectionMatrix();

  renderer.setSize(width, height);
}

function animate() {
  if (!animationStarted || !controls || !renderer) return;

  requestAnimationFrame(animate);

  controls.update();
  renderer.render(scene, camera);
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

  // Reusable materials for all 21 components.
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

  const B = (w, h, d, material, x, y, z) =>
    box(group, w, h, d, material, x, y, z);

  // CylinderGeometry's default axis is Y.
  const C = (radius, length, material, x, y, z, axis = "y", segments = 24) => {
    const mesh = new THREE.Mesh(
      new THREE.CylinderGeometry(radius, radius, length, segments),
      material
    );

    if (axis === "x") mesh.rotation.z = Math.PI / 2;
    if (axis === "z") mesh.rotation.x = Math.PI / 2;

    mesh.position.set(x, y, z);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    group.add(mesh);
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
      C(0.035, 0.25, silver, 0, 0.7, 0.44, "z");
      break;

    // 2. Basic robot wheel
    case "wheel_basic":
    case "space_rover_wheel": {
      const rover = id === "space_rover_wheel";
      const radius = rover ? 0.4 : 0.34;
      const width = rover ? 0.28 : 0.2;

      C(radius, width, rubber, 0, radius, 0, "x", 40);
      C(radius * 0.68, width + 0.02, silver, 0, radius, 0, "x", 32);
      C(radius * 0.36, width + 0.05, gold, 0, radius, 0, "x", 24);

      // Tread blocks around the wheel.
      for (let i = 0; i < 16; i++) {
        const a = (i / 16) * Math.PI * 2;
        const tread = B(
          width * 1.12,
          rover ? 0.1 : 0.065,
          rover ? 0.075 : 0.045,
          dark,
          Math.cos(a) * radius,
          radius + Math.sin(a) * radius,
          0
        );
        tread.rotation.z = -a;
      }

      for (let i = 0; i < 6; i++) {
        const a = (i / 6) * Math.PI * 2;
        C(
          0.025, width + 0.055, dark,
          Math.cos(a) * radius * 0.47,
          radius + Math.sin(a) * radius * 0.47,
          0, "x", 10
        );
      }
      break;
    }

    // 3. 12 V battery pack
    case "battery_basic":
      B(0.64, 0.34, 0.78, green, 0, 0.48, 0);
      B(0.58, 0.04, dark, 0, 0.67, 0);
      B(0.42, 0.025, white, 0, 0.695, 0);
      C(0.045, 0.07, gold, -0.18, 0.72, -0.2);
      C(0.045, 0.07, silver, 0.18, 0.72, -0.2);
      B(0.26, 0.035, dark, 0, 0.25, 0.4);
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
      B(0.08, 0.025, gold, 0, 0.45, -0.1);
      break;

    // 6. Geared DC motor
    case "motor_geared":
      C(0.14, 0.32, silver, 0, 0.62, -0.08, "z");
      C(0.19, 0.19, gold, 0, 0.62, 0.18, "z", 12);
      C(0.075, 0.22, silver, 0, 0.62, 0.38, "z");
      B(0.32, 0.04, dark, 0, 0.43, 0.05);
      C(0.035, 0.12, gold, 0, 0.62, 0.52, "z");
      break;

    // 7. Servo motor
    case "servo_basic":
      B(0.25, 0.17, 0.2, blue, 0, 0.52, 0);
      B(0.2, 0.035, dark, 0, 0.62, 0);
      C(0.035, 0.09, silver, 0, 0.69, 0);
      B(0.28, 0.025, white, 0, 0.75, 0);
      C(0.025, 0.04, gold, -0.11, 0.75, 0);
      C(0.025, 0.04, gold, 0.11, 0.75, 0);
      break;

    // 8. Stepper motor
    case "stepper_basic":
      B(0.38, 0.38, 0.3, silver, 0, 0.55, 0);
      B(0.32, 0.06, dark, 0, 0.55, 0.17);
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
      B(0.12, 0.035, dark, 0, 0.43, 0);
      break;

    // 10. IMU sensor board
    case "sensor_imu":
      B(0.28, 0.045, 0.28, pcb, 0, 0.48, 0);
      B(0.11, 0.045, black, 0, 0.53, 0);
      for (const x of [-0.1, 0.1]) {
        for (const z of [-0.1, 0.1]) {
          C(0.018, 0.035, gold, x, 0.52, z);
        }
      }
      B(0.06, 0.025, silver, 0, 0.57, 0);
      break;

    // 11. Light sensor
    case "sensor_light":
      B(0.22, 0.06, 0.2, pcb, 0, 0.48, 0);
      C(0.065, 0.055, black, 0, 0.54, 0, "y");
      S(0.045, cyan, 0, 0.58, 0);
      B(0.08, 0.025, gold, 0, 0.44, 0.11);
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
      B(0.16, 0.06, black, 0, 0.535, 0);
      B(0.11, 0.025, silver, 0, 0.58, 0);
      for (const x of [-0.16, 0.16]) {
        B(0.045, 0.06, gold, x, 0.53, -0.16);
        B(0.045, 0.06, gold, x, 0.53, 0.16);
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
      B(0.12, 0.035, black, 0, 0.54, -0.08);
      for (const x of [-0.12, 0.12]) {
        C(0.018, 0.05, gold, x, 0.52, 0.16);
      }
      break;

    // 16. Spacecraft solar panel
    case "space_solar_panel":
      B(0.12, 0.08, 0.12, silver, 0, 0.52, 0);
      B(0.58, 0.035, dark, -0.43, 0.52, 0);
      B(0.58, 0.035, dark, 0.43, 0.52, 0);

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
      B(0.28, 0.06, dark, 0, 0.47, 0);
      break;

    // 18. Planetary science sensor
    case "space_sensor":
      B(0.36, 0.22, 0.3, silver, 0, 0.58, 0);
      B(0.26, 0.12, dark, 0, 0.75, 0);
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
      B(0.34, 0.06, silver, 0, 0.84, 0);
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

    // 21. Safe fallback for future or unrecognized component IDs
    default: {
      const color = new THREE.Color().setHSL(
        (part.instanceId.length * 0.13) % 1, 0.65, 0.55
      );
      const material = mat(color, 0.25, 0.55);
      B(0.4, 0.4, 0.4, material, 0, 0.5, 0);
      B(0.3, 0.04, silver, 0, 0.72, 0);
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
    mass: Number(component.mass_kg) || 0
  };

  part.group = geometry(part);

  const pos = position || defaultPos(id);
  part.group.position.set(pos.x, pos.y, pos.z);
  part.basePosition = { x: pos.x, y: pos.y, z: pos.z };

  scene.add(part.group);
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
    select(hit.object.userData.id);
  }
}

function select(id) {
  selected = parts.find(part => part.instanceId === id) || null;

  setHidden("empty", !!selected);
  setHidden("inspector", !selected);

  if (transformControls) {
    if (selected) {
      transformControls.attach(selected.group);

      // Re-apply the chosen mode so selecting a part never changes it.
      setTransformMode(transformMode);
    } else {
      transformControls.detach();
    }
  }

  if (selected) {
    writeInspector();
  } else {
    inspectorSnapshot = {};
  }

  render();
}

function writeInspector() {
  if (!selected) return;

  const group = selected.group;

  setText("part-name", selected.name);
  setText(
    "part-id",
    selected.componentId + " · " + selected.mass.toFixed(2) + " kg"
  );

  // Yaw is read with Euler order YXZ so it stays correct beyond ±90°
  // (the default XYZ order folds Y into that range).
  const yaw = THREE.MathUtils.radToDeg(
    new THREE.Euler().setFromQuaternion(group.quaternion, "YXZ").y
  );

  // The inspector has one uniform scale field. A non-uniform scale from
  // the gizmo is shown as "mixed" instead of a wrong number.
  const s = group.scale;
  const uniform =
    Math.abs(s.x - s.y) < 1e-4 && Math.abs(s.y - s.z) < 1e-4;

  inspectorSnapshot = {
    x: fixed(group.position.x, 2),
    y: fixed(group.position.y, 2),
    z: fixed(group.position.z, 2),
    rot: String(Math.round(yaw) || 0),
    scale: uniform ? fixed(s.x, 2) : ""
  };

  for (const [id, value] of Object.entries(inspectorSnapshot)) {
    const input = $(id);

    // Do not overwrite a field the user is typing in.
    if (input && input !== document.activeElement) {
      input.value = value;
    }
  }

  const scaleInput = $("scale");
  if (scaleInput) scaleInput.placeholder = uniform ? "" : "mixed";
}

function transform() {
  if (!selected) return;

  const rules = [
    ["x", -20, 20, "Position X must be within ±20 metres."],
    ["y", -20, 20, "Position Y must be within ±20 metres."],
    ["z", -20, 20, "Position Z must be within ±20 metres."],
    ["rot", -36000, 36000, "Rotation must be within ±36000 degrees."],
    ["scale", SCALE_MIN, SCALE_MAX,
      `Scale must be between ${SCALE_MIN} and ${SCALE_MAX}.`]
  ];

  // Collect only the fields the user changed.
  const changes = {};

  for (const [id, min, max, message] of rules) {
    const input = $(id);
    if (!input) continue;

    const text = input.value.trim();
    if (text === (inspectorSnapshot[id] ?? "")) continue;

    const value = Number(text);

    if (text === "" || !Number.isFinite(value) || value < min || value > max) {
      alert(message);
      return;
    }

    changes[id] = value;
  }

  if (Object.keys(changes).length === 0) return;

  invalidateSimulation();

  const group = selected.group;

  if ("x" in changes) group.position.x = changes.x;
  if ("y" in changes) group.position.y = changes.y;
  if ("z" in changes) group.position.z = changes.z;

  selected.basePosition = {
    x: group.position.x,
    y: group.position.y,
    z: group.position.z
  };

  if ("rot" in changes) {
    // Replace only the yaw and keep any other orientation as it is.
    const euler = new THREE.Euler().setFromQuaternion(group.quaternion, "YXZ");
    euler.y = THREE.MathUtils.degToRad(changes.rot);
    group.quaternion.setFromEuler(euler);
  }

  if ("scale" in changes) group.scale.setScalar(changes.scale);

  writeInspector();
  render();
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

  scene.remove(removed.group);
  disposePart(removed);
  parts = parts.filter(part => part !== removed);

  update();
}

function resetScene() {
  if (!scene) return;

  stopTrajectoryPlayback(true);
  trajectoryPlayback = null;
  invalidateSimulation();
  select(null);

  for (const part of parts) {
    scene.remove(part.group);
    disposePart(part);
  }

  parts = [];
  nextId = 1;
  simulatedSlopeDegrees = 0;

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
  const libraryFilter = $("library-filter");
  const categoryFilter = $("category-filter");
  const libraryCount = $("library-count");

  function populateCategories() {
    if (!categoryFilter) return;

    const previousCategory = categoryFilter.value || "all";
    const categories = [...new Set(
      catalog.map(component => component.category).filter(Boolean)
    )].sort();

    categoryFilter.innerHTML = '<option value="all">All categories</option>';

    for (const category of categories) {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = categoryLabels[category] || category;
      categoryFilter.append(option);
    }

    categoryFilter.value = categories.includes(previousCategory)
      ? previousCategory
      : "all";
  }

  function renderComponents() {
    const query = (searchInput?.value || "").trim().toLowerCase();
    const selectedLibrary = libraryFilter?.value || "all";
    const selectedCategory = categoryFilter?.value || "all";

    const filtered = catalog.filter(component => {
      const matchesSearch = [
        component.name,
        component.id,
        component.category,
        component.description,
        ...asArray(component.tags)
      ].some(value => String(value || "").toLowerCase().includes(query));

      const matchesLibrary =
        selectedLibrary === "all" ||
        (component.library || "engineering") === selectedLibrary;

      const matchesCategory =
        selectedCategory === "all" ||
        component.category === selectedCategory;

      return matchesSearch && matchesLibrary && matchesCategory;
    });

    if (list) {
      list.innerHTML = "";

      for (const component of filtered) {
        const id = component.id;

        const symbols = {
          actuator: "⚙",
          mechanical: "◉",
          power: "▣",
          structure: "▰",
          sensor: "⌁",
          electrical: "ϟ",
          robotics: "🤖",
          aerospace: "🚀",
          space: "🛰"
        };

        const button = document.createElement("button");
        button.type = "button";
        button.className = "component-card";
        button.dataset.componentId = id;
        button.draggable = true;

        const icon = document.createElement("span");
        icon.textContent = symbols[component.category] || "◈";

        const details = document.createElement("div");
        const strong = document.createElement("strong");
        const small = document.createElement("small");

        strong.textContent = component.name || id;

        const mass = Number(component.mass_kg) || 0;
        const libraryName = component.library === "space"
          ? "Space"
          : "Engineering";

        small.textContent =
          `${mass.toFixed(2)} kg · ${libraryName} · click to add`;

        details.append(strong, small);
        button.append(icon, details);

        button.addEventListener("click", () => add(id));
        list.append(button);
      }
    }

    if (libraryCount) {
      libraryCount.textContent =
        `Showing ${filtered.length} of ${catalog.length} components`;
    }
  }

  populateCategories();
  renderComponents();

  searchInput?.addEventListener("input", renderComponents);
  libraryFilter?.addEventListener("change", renderComponents);
  categoryFilter?.addEventListener("change", renderComponents);

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

  const motorParts = parts.filter(isMotorPart);
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
    for (const part of parts) {
      if (part.basePosition && part.group) {
        part.group.position.set(
          part.basePosition.x,
          part.basePosition.y,
          part.basePosition.z
        );
      }
    }
    if (selected) writeInspector();
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
  if (selected) writeInspector();
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

    for (const part of parts) {
      if (part.basePosition && part.group) {
        part.group.position.x = part.basePosition.x;
        part.group.position.y = part.basePosition.y + deltaY;
        part.group.position.z = part.basePosition.z + deltaZ;
      }
    }

    if (selected) writeInspector();
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

  currentDriveDirection = null;
}

function driveRobot(direction) {
  const chassis = parts.find(
    part => part.componentId === "chassis_basic"
  );

  if (
    !chassis ||
    countParts(isMotorPart) === 0 ||
    countParts(isWheelPart) < 2
  ) {
    setText(
      "drive-status",
      "Add a chassis, at least one motor and two wheels."
    );
    return;
  }

  if (direction === "stop") {
    if (trajectoryPlayback && trajectoryPlayback.active) {
      stopTrajectoryPlayback(false);
      setText(
        "drive-status",
        "Trajectory playback paused. Click Stop again to reset to origin."
      );
      return;
    } else if (trajectoryPlayback && !trajectoryPlayback.active) {
      stopTrajectoryPlayback(true);
      trajectoryPlayback = null;
      stopRobot();
      setText("drive-status", "Robot stopped and reset to assembly origin.");
      return;
    }

    stopRobot();
    setText("drive-status", "Robot stopped");
    return;
  }

  // If manual driving starts while trajectory playback is active, halt trajectory playback
  if (trajectoryPlayback && trajectoryPlayback.active) {
    stopTrajectoryPlayback(false);
  }

  for (const part of parts) {
    if (part.group) {
      part.basePosition = {
        x: part.group.position.x,
        y: part.group.position.y,
        z: part.group.position.z
      };
    }
  }

  if (
    simulatedAcceleration === null ||
    !Number.isFinite(simulatedAcceleration)
  ) {
    setText("drive-status", "Run the simulation first.");
    return;
  }

  if (simulatedAcceleration <= 0) {
    setText(
      "drive-status",
      "Insufficient modeled acceleration. Check simulation results."
    );
    return;
  }

  const movement = {
    forward: [0, -1],
    backward: [0, 1],
    left: [-1, 0],
    right: [1, 0]
  };

  const vector = movement[direction];
  if (!vector) return;

  if (driveTimer && currentDriveDirection === direction) return;

  stopRobot();
  currentDriveDirection = direction;

  const dt = 0.03;
  const maxSpeed = 2;
  let velocity = 0;

  const visualAcceleration = Math.min(simulatedAcceleration, 0.3);

  driveTimer = setInterval(() => {
    velocity = Math.min(velocity + visualAcceleration * dt, maxSpeed);
    const distance = velocity * dt;

    parts.forEach(part => {
      part.group.position.x += vector[0] * distance;
      part.group.position.z += vector[1] * distance;
      part.basePosition = {
        x: part.group.position.x,
        y: part.group.position.y,
        z: part.group.position.z
      };
    });

    // Keep the inspector in step with the moving part.
    if (selected) writeInspector();
  }, dt * 1000);

  setText(
    "drive-status",
    "Driving: " + direction + " | Visual steering (scaled acceleration, not physical trajectory)"
  );
}

document.querySelectorAll("[data-drive]").forEach(button => {
  button.addEventListener("click", () => {
    driveRobot(button.dataset.drive);
  });
});

document.addEventListener("keydown", event => {
  if (
    ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)
  ) {
    return;
  }

  // Some synthetic events (for example autofill) have no key.
  if (!event.key) return;

  if (event.key === "Escape") {
    if (selected) select(null);
    return;
  }

  const keys = {
    w: "forward",
    ArrowUp: "forward",
    s: "backward",
    ArrowDown: "backward",
    a: "left",
    ArrowLeft: "left",
    d: "right",
    ArrowRight: "right"
  };

  if (event.code === "Space") {
    event.preventDefault();
    driveRobot("stop");
    return;
  }

  const direction = keys[event.key] || keys[event.key.toLowerCase()];

  if (direction) {
    event.preventDefault();
    driveRobot(direction);
  }
});

// --------------------------------------------------
// BUTTON HANDLERS
// --------------------------------------------------

on("apply", "click", transform);
on("remove", "click", removeSelected);
on("simulate", "click", simulate);
on("reset", "click", resetScene);

// Enter inside an inspector field applies the transform.
for (const id of ["x", "y", "z", "rot", "scale"]) {
  on(id, "keydown", event => {
    if (event.key === "Enter") {
      event.preventDefault();
      transform();
    }
  });
}

// --------------------------------------------------
// START APPLICATION
// --------------------------------------------------

// Report missing HTML elements once instead of failing later.
const EXPECTED_IDS = [
  "viewport", "component-list", "part-count", "mass", "motors", "wheels",
  "inspector", "empty", "x", "y", "z", "rot", "scale", "apply", "remove",
  "simulate", "reset", "result-message", "result-grid", "analysis",
  "driving", "gravity", "net", "accel", "drive-status", "api-status",
  "final-velocity", "distance-traveled", "wheel-rotations", "wheel-rpm",
  "move-tool", "rotate-tool", "scale-tool", "transform-mode",
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
  init();
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
