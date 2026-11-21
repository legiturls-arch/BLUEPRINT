import * as THREE from "./vendor/three.module.js";
import { OrbitControls } from "./vendor/OrbitControls.js";

const host = document.getElementById("assembly-viewport");
const status = document.getElementById("assembly-viewport-status");
const robotSelect = document.getElementById("robot-select");

if (!host || !robotSelect) {
  throw new Error("Missing Testing Lab assembly viewport elements.");
}

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b1525);

const camera = new THREE.PerspectiveCamera(48, 1, 0.005, 1000);
camera.position.set(5.5, 4.5, 7);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
host.prepend(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.target.set(0, 0.5, 0);
controls.minDistance = 0.01;
controls.maxDistance = 35;

scene.add(new THREE.HemisphereLight(0xcbe9ff, 0x26344a, 1.8));
const keyLight = new THREE.DirectionalLight(0xffffff, 2.2);
keyLight.position.set(5, 8, 6);
keyLight.castShadow = true;
scene.add(keyLight);

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(30, 30),
  new THREE.MeshStandardMaterial({ color: 0x111d2d, roughness: 0.9 })
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.02;
ground.receiveShadow = true;
scene.add(ground);

const grid = new THREE.GridHelper(30, 30, 0x34526e, 0x1c2d42);
grid.position.y = -0.012;
scene.add(grid);

let assemblyRoot = new THREE.Group();
scene.add(assemblyRoot);
let catalog = [];
let defaultView = null;

function readJson(key, fallback) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null");
    return value ?? fallback;
  } catch (error) {
    console.warn(`Could not read ${key}:`, error);
    return fallback;
  }
}

function material(color, metalness = 0.25, roughness = 0.55) {
  return new THREE.MeshStandardMaterial({ color, metalness, roughness });
}

function addMesh(group, geometry, finish, position, rotation) {
  const mesh = new THREE.Mesh(geometry, finish);
  if (position) mesh.position.set(position.x || 0, position.y || 0, position.z || 0);
  if (rotation) mesh.rotation.set(rotation.x || 0, rotation.y || 0, rotation.z || 0);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  group.add(mesh);
  return mesh;
}

function createPartGeometry(component, savedPart) {
  const group = new THREE.Group();
  const id = component?.id || savedPart.componentId;
  const category = component?.category || "other";
  const body = material(
    id.includes("chassis") ? 0x4d83c6 :
    category === "power" ? 0xd7a84b :
    category === "sensor" ? 0x45d6c4 :
    category === "mechanical" ? 0x71839a :
    category === "actuator" ? 0x7ca2ca :
    category === "structure" ? 0x8fa4bd :
    0x56a4ce,
    category === "structure" ? 0.5 : 0.25,
    0.55
  );
  const dark = material(0x1b2533, 0.15, 0.75);
  const rubber = material(0x171b22, 0.05, 0.92);

  if (id === "wheel_basic" || id === "wheel_planetary" || id.includes("wheel")) {
    addMesh(group, new THREE.CylinderGeometry(
      Number(component?.radius_m || 0.08),
      Number(component?.radius_m || 0.08),
      0.08,
      24
    ), rubber, { x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: Math.PI / 2 });
  } else if (category === "actuator" || id.includes("motor")) {
    addMesh(group, new THREE.CylinderGeometry(0.09, 0.09, 0.28, 24), body,
      { x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: Math.PI / 2 });
    addMesh(group, new THREE.CylinderGeometry(0.045, 0.045, 0.08, 20), dark,
      { x: 0.18, y: 0, z: 0 }, { x: 0, y: 0, z: Math.PI / 2 });
  } else if (category === "sensor") {
    addMesh(group, new THREE.BoxGeometry(0.16, 0.1, 0.18), body,
      { x: 0, y: 0.05, z: 0 });
    addMesh(group, new THREE.CylinderGeometry(0.035, 0.035, 0.012, 16), dark,
      { x: 0, y: 0.05, z: 0.092 }, { x: Math.PI / 2, y: 0, z: 0 });
  } else if (category === "power") {
    addMesh(group, new THREE.BoxGeometry(0.28, 0.16, 0.18), body,
      { x: 0, y: 0.08, z: 0 });
  } else if (id.includes("chassis") || category === "structure") {
    addMesh(group, new THREE.BoxGeometry(
      id.includes("rover") || id.includes("satellite") ? 0.9 : 1.2,
      id.includes("frame") ? 0.08 : 0.12,
      id.includes("rover") || id.includes("satellite") ? 0.65 : 0.8
    ), body, { x: 0, y: 0.06, z: 0 });
  } else if (category === "mechanical") {
    addMesh(group, new THREE.CylinderGeometry(0.12, 0.12, 0.08, 16), body,
      { x: 0, y: 0.06, z: 0 });
  } else if (category === "electrical" || category === "lighting") {
    addMesh(group, new THREE.BoxGeometry(0.22, 0.06, 0.16), body,
      { x: 0, y: 0.03, z: 0 });
    if (id.includes("led")) {
      addMesh(group, new THREE.SphereGeometry(0.055, 16, 10),
        material(savedPart.ledColor ? Number.parseInt(savedPart.ledColor.replace("#", ""), 16) : 0x45d6e8, 0.2, 0.25),
        { x: 0, y: 0.08, z: 0.09 });
    }
  } else {
    addMesh(group, new THREE.BoxGeometry(0.22, 0.12, 0.22), body,
      { x: 0, y: 0.06, z: 0 });
  }

  group.userData.componentId = id;
  return group;
}

function clearAssembly() {
  scene.remove(assemblyRoot);
  assemblyRoot.traverse(object => {
    if (object.isMesh) {
      object.geometry?.dispose();
      if (Array.isArray(object.material)) object.material.forEach(item => item.dispose());
      else object.material?.dispose();
    }
  });
  assemblyRoot = new THREE.Group();
  assemblyRoot.name = "robot-assembly";
  scene.add(assemblyRoot);
}

function fitAssembly() {
  const box = new THREE.Box3().setFromObject(assemblyRoot);
  if (box.isEmpty()) return;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const radius = Math.max(size.length(), 0.8);
  controls.target.copy(center);
  camera.position.copy(center.clone().add(new THREE.Vector3(radius * 0.9, radius * 0.7, radius * 1.1)));
  camera.lookAt(center);
  controls.update();
  controls.saveState();
  defaultView = {
    position: camera.position.clone(),
    target: controls.target.clone()
  };
}

function findAssembly(snapshot) {
  if (snapshot?.assembly?.parts && Array.isArray(snapshot.assembly.parts)) {
    return snapshot.assembly;
  }

  const savedDesign = readJson("blueprint_saved_design", null);
  if (!savedDesign?.parts || !Array.isArray(savedDesign.parts)) return null;
  if (!snapshot?.component_ids) return savedDesign;

  const snapshotIds = [...snapshot.component_ids].sort();
  const designIds = [...savedDesign.parts.map(part => part.componentId)].sort();
  if (snapshotIds.length !== designIds.length) return null;
  return snapshotIds.every((id, index) => id === designIds[index]) ? savedDesign : null;
}

function renderAssembly() {
  clearAssembly();
  const snapshots = readJson("blueprint_testing_robots", []);
  if (!Array.isArray(snapshots)) {
    setViewportStatus("No saved builder assembly found");
    return;
  }

  const snapshot = snapshots.find(item => item.id === robotSelect.value);
  if (!snapshot) {
    setViewportStatus("Select a saved builder assembly");
    return;
  }

  const assembly = findAssembly(snapshot);
  if (!assembly?.parts?.length) {
    setViewportStatus("Saved assembly geometry is unavailable");
    return;
  }

  let rendered = 0;
  for (const savedPart of assembly.parts) {
    const component = catalog.find(item => item.id === savedPart.componentId);
    if (!component) continue;
    const part = createPartGeometry(component, savedPart);
    const position = savedPart.position || {};
    const rotation = savedPart.rotation || {};
    const scale = savedPart.scale || {};
    part.position.set(position.x || 0, position.y || 0, position.z || 0);
    part.rotation.set(rotation.x || 0, rotation.y || 0, rotation.z || 0);
    part.scale.set(scale.x || 1, scale.y || 1, scale.z || 1);
    assemblyRoot.add(part);
    rendered += 1;
  }

  if (!rendered) {
    setViewportStatus("Saved assembly components could not be loaded");
    return;
  }

  setViewportStatus("");
  fitAssembly();
}

function setViewportStatus(message) {
  if (!status) return;
  status.textContent = message;
  status.hidden = !message;
}

function resize() {
  const width = Math.max(host.clientWidth, 1);
  const height = Math.max(host.clientHeight, 1);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

robotSelect.addEventListener("change", renderAssembly);
document.getElementById("assembly-reset-view")?.addEventListener("click", () => {
  if (defaultView) {
    camera.position.copy(defaultView.position);
    controls.target.copy(defaultView.target);
    controls.update();
  }
});
document.getElementById("assembly-fit-view")?.addEventListener("click", fitAssembly);

if ("ResizeObserver" in window) {
  new ResizeObserver(resize).observe(host);
}
resize();

function animate() {
  controls.update();
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}
animate();

async function loadCatalog() {
  try {
    const response = await fetch(`${location.origin}/api/components`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    catalog = Array.isArray(data.components) ? data.components : [];
  } catch (error) {
    console.error("Could not load component geometry catalog:", error);
  }
  renderAssembly();
}

window.BlueprintTestingViewport = {
  refresh: renderAssembly,
  fit: fitAssembly
};

loadCatalog();
