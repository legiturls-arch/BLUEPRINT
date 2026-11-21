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
const environmentRoot = new THREE.Group();
environmentRoot.name = "testing-environment";
scene.add(environmentRoot);
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

const environmentDefinitions = [
  { id:"flat-concrete", name:"Flat Concrete", category:"Industrial", difficulty:"Basic",
    description:"Large flat concrete test ground with measurement markings and clear industrial surroundings.",
    terrain:"flat_concrete", capabilities:["Basic mobility","Motor performance","Speed testing","Straight-line movement"],
    config:[{key:"testLength",label:"Test length (m)",type:"number",value:12,min:2,max:30,step:1}] },
  { id:"rocky-terrain", name:"Rocky Terrain", category:"Outdoor", difficulty:"Advanced",
    description:"Uneven natural terrain with varied rock sizes for rover mobility and clearance testing.",
    terrain:"rocky_terrain", capabilities:["Ground clearance","Wheel traction","Suspension","Terrain mobility"],
    config:[{key:"rockSize",label:"Rock size (cm)",type:"number",value:18,min:5,max:50,step:1},{key:"roughness",label:"Terrain roughness",type:"range",value:55,min:10,max:100,step:5}] },
  { id:"desert-terrain", name:"Desert Terrain", category:"Outdoor", difficulty:"Intermediate",
    description:"Sandy landscape with medium dunes and elevation changes for traction and climb testing.",
    terrain:"sand", capabilities:["Wheel traction","Sand mobility","Motor load","Climbing"],
    config:[{key:"duneHeight",label:"Dune height (m)",type:"number",value:.8,min:.1,max:2,step:.1}] },
  { id:"inclined-ramp", name:"Inclined Ramp", category:"Industrial", difficulty:"Intermediate",
    description:"Adjustable concrete and metal ramp surface for torque and stability testing.",
    terrain:"rough_concrete", capabilities:["Climbing","Torque requirement","Slope resistance","Stability"],
    config:[{key:"slopeAngle",label:"Slope angle (degrees)",type:"number",value:20,min:5,max:45,step:1},{key:"rampLength",label:"Ramp length (m)",type:"number",value:8,min:2,max:15,step:.5}] },
  { id:"obstacle-course", name:"Obstacle Course", category:"Mobility", difficulty:"Advanced",
    description:"Concrete barriers, blocks, narrow paths and ramps for collision and navigation tests.",
    terrain:"rough_concrete", capabilities:["Obstacle clearance","Collision detection","Navigation","Mobility"],
    config:[{key:"obstacleHeight",label:"Obstacle height (m)",type:"number",value:.25,min:.05,max:1,step:.05},{key:"obstacleSpacing",label:"Obstacle spacing (m)",type:"number",value:2,min:.5,max:5,step:.1}] },
  { id:"uneven-terrain", name:"Uneven Terrain", category:"Outdoor", difficulty:"Advanced",
    description:"Natural hills and depressions with changing elevation for suspension and contact tests.",
    terrain:"loose_soil", capabilities:["Stability","Suspension","Wheel contact","Adaptability"],
    config:[{key:"hillHeight",label:"Hill height (m)",type:"number",value:.6,min:.1,max:1.5,step:.1},{key:"surfaceVariation",label:"Surface variation",type:"range",value:60,min:10,max:100,step:5}] },
  { id:"gravel-road", name:"Gravel Road", category:"Outdoor", difficulty:"Intermediate",
    description:"Loose stone road with irregular small aggregates for grip and rolling resistance tests.",
    terrain:"gravel", capabilities:["Traction","Wheel grip","Motor performance","Surface resistance"],
    config:[{key:"stoneSize",label:"Stone size (cm)",type:"number",value:3,min:.5,max:10,step:.5}] },
  { id:"mud-terrain", name:"Mud Terrain", category:"Outdoor", difficulty:"Advanced",
    description:"Soft muddy track with wet patches, wheel ruts and irregular elevation.",
    terrain:"mud", capabilities:["Traction estimation","Wheel slip","Mobility limits","Motor load"],
    config:[{key:"mudDepth",label:"Mud depth (cm)",type:"number",value:8,min:1,max:30,step:1},{key:"patchCount",label:"Mud patch count",type:"number",value:12,min:3,max:30,step:1}] },
  { id:"sand-obstacle-course", name:"Sand Obstacle Course", category:"Mobility", difficulty:"Advanced",
    description:"Sandy dunes and barrier sections combining climbing and obstacle clearance.",
    terrain:"sand", capabilities:["Sand climbing","Obstacle clearance","Traction","Mobility"],
    config:[{key:"obstacleHeight",label:"Obstacle height (m)",type:"number",value:.3,min:.05,max:1,step:.05},{key:"duneHeight",label:"Dune height (m)",type:"number",value:.7,min:.1,max:2,step:.1}] },
  { id:"industrial-test-track", name:"Industrial Test Track", category:"Industrial", difficulty:"Intermediate",
    description:"Indoor controlled facility with concrete floor, platforms and metal ramps.",
    terrain:"rough_concrete", capabilities:["Controlled mobility","Payload testing","Structural testing","Motor performance"],
    config:[{key:"rampAngle",label:"Ramp angle (degrees)",type:"number",value:15,min:5,max:35,step:1},{key:"platformHeight",label:"Platform height (m)",type:"number",value:.5,min:.1,max:1.5,step:.1}] },
  { id:"stairs-steps", name:"Stairs and Steps", category:"Mobility", difficulty:"Advanced",
    description:"Multiple concrete step configurations for ground clearance and stability testing.",
    terrain:"rough_concrete", capabilities:["Step climbing","Ground clearance","Stability","Wheel geometry"],
    config:[{key:"stepHeight",label:"Step height (m)",type:"number",value:.18,min:.05,max:.5,step:.01},{key:"stepWidth",label:"Step width (m)",type:"number",value:.35,min:.15,max:.8,step:.05},{key:"stepCount",label:"Number of steps",type:"number",value:5,min:2,max:10,step:1}] },
  { id:"custom-arena", name:"Custom Testing Arena", category:"Custom", difficulty:"Intermediate",
    description:"Open configurable arena with sections, measurement marks and removable challenge sections.",
    terrain:"flat_concrete", capabilities:["Custom obstacles","Combined mobility","Experimental setup"],
    config:[{key:"arenaSize",label:"Arena size (m)",type:"number",value:16,min:8,max:30,step:1},{key:"challengeCount",label:"Challenge sections",type:"number",value:4,min:1,max:8,step:1}] }
];

const envConfig = new Map();

function disposeGroup(group) {
  group.traverse(object => {
    if (!object.isMesh) return;
    object.geometry?.dispose();
    if (Array.isArray(object.material)) object.material.forEach(item => item.dispose());
    else object.material?.dispose();
  });
  group.clear();
}

function addBox(parent, size, position, color, roughness=.75) {
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(size.x, size.y, size.z),
    new THREE.MeshStandardMaterial({ color, roughness, metalness: roughness < .5 ? .5 : .05 })
  );
  mesh.position.set(position.x, position.y, position.z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function getConfig(id) {
  const def = environmentDefinitions.find(item => item.id === id);
  return { ...(Object.fromEntries(def.config.map(item => [item.key,item.value]))), ...(envConfig.get(id) || {}) };
}

function buildEnvironment(id) {
  disposeGroup(environmentRoot);
  const def = environmentDefinitions.find(item => item.id === id) || environmentDefinitions[0];
  const cfg = getConfig(def.id);
  const base = def.id === "desert-terrain" || def.id === "sand-obstacle-course" ? 0xc79655
    : def.id === "mud-terrain" ? 0x66513e
    : def.id === "gravel-road" ? 0x777269
    : def.id === "rocky-terrain" ? 0x68675f
    : def.id === "uneven-terrain" ? 0x747d5a
    : 0x68727a;
  ground.material.color.setHex(base);
  grid.visible = def.id === "flat-concrete" || def.id === "industrial-test-track" || def.id === "custom-arena";

  if (def.id === "flat-concrete" || def.id === "custom-arena") {
    const length = def.id === "custom-arena" ? cfg.arenaSize : cfg.testLength;
    for (let i=-Math.floor(length/2); i<=length/2; i+=1) {
      addBox(environmentRoot,{x:.025,y:.006,z:18},{x:i,y:.002,z:0},0xd4dddc,.9);
    }
    for (let i=-9;i<=9;i+=1) addBox(environmentRoot,{x:length,y:.006,z:.025},{x:0,y:.003,z:i},0xd4dddc,.9);
  }

  if (def.id === "rocky-terrain") {
    for (let i=0;i<90;i++) {
      const x=(Math.random()-.5)*22,z=(Math.random()-.5)*18;
      const s=.08+(cfg.rockSize/100)*(0.35+Math.random()*0.8);
      const rock=new THREE.Mesh(new THREE.DodecahedronGeometry(s,0),new THREE.MeshStandardMaterial({color:0x77766d,roughness:.95}));
      rock.position.set(x,s*.38+.04,z); rock.rotation.set(Math.random(),Math.random(),Math.random()); rock.castShadow=rock.receiveShadow=true;
      environmentRoot.add(rock);
    }
  }

  if (def.id === "desert-terrain" || def.id === "sand-obstacle-course") {
    for (let i=-3;i<=3;i++) {
      const dune=new THREE.Mesh(new THREE.SphereGeometry(2.4,20,10,0,Math.PI*2,0,Math.PI/2),new THREE.MeshStandardMaterial({color:i%2?0xd1a86d:0xb98a4f,roughness:1}));
      dune.scale.set(1.7,cfg.duneHeight/2,1); dune.position.set(i*4,-.05,(i%2)*3-1); dune.receiveShadow=true;
      environmentRoot.add(dune);
    }
  }

  if (def.id === "inclined-ramp" || def.id === "industrial-test-track") {
    const angle=(def.id==="inclined-ramp"?cfg.slopeAngle:cfg.rampAngle)*Math.PI/180;
    const rampLength=def.id==="inclined-ramp"?cfg.rampLength:7;
    const ramp=addBox(environmentRoot,{x:rampLength,y:.12,z:4},{x:2,y:0,z:0},0x7b8588,.55);
    ramp.position.y=rampLength*Math.sin(angle)/2;
    ramp.rotation.z=-angle;
  }

  if (def.id === "obstacle-course" || def.id === "sand-obstacle-course") {
    for (let i=-2;i<=2;i++) {
      const height=cfg.obstacleHeight||.25;
      addBox(environmentRoot,{x:1.2,y:height,z:1.2},{x:i*cfg.obstacleSpacing,y:height/2,z:(i%2)*2},0x7d8788,.8);
    }
  }

  if (def.id==="uneven-terrain") {
    for(let i=-4;i<=4;i++){
      const h=cfg.hillHeight*(.35+Math.random()*1);
      const hill=new THREE.Mesh(new THREE.CylinderGeometry(.9,2,h,12),new THREE.MeshStandardMaterial({color:0x697252,roughness:1}));
      hill.position.set(i*2,h/2-.02,(i%2)*2); hill.scale.z=1.4; hill.receiveShadow=hill.castShadow=true; environmentRoot.add(hill);
    }
  }

  if(def.id==="gravel-road"){
    for(let i=0;i<260;i++){
      const s=.025+(cfg.stoneSize/100)*(.5+Math.random());
      const stone=new THREE.Mesh(new THREE.DodecahedronGeometry(s,0),new THREE.MeshStandardMaterial({color:0x8b8375,roughness:1}));
      stone.position.set((Math.random()-.5)*18,-.005,(Math.random()-.5)*10); stone.rotation.set(Math.random(),Math.random(),Math.random()); stone.receiveShadow=true; environmentRoot.add(stone);
    }
  }

  if(def.id==="mud-terrain"){
    for(let i=0;i<cfg.patchCount;i++){
      const patch=new THREE.Mesh(new THREE.CircleGeometry(.5+Math.random()*1.1,20),new THREE.MeshStandardMaterial({color:0x483729,roughness:.25,metalness:.05}));
      patch.rotation.x=-Math.PI/2; patch.position.set((Math.random()-.5)*18,.012,(Math.random()-.5)*12); patch.scale.set(1.4+.5*Math.random(),.5+.5*Math.random(),1); patch.receiveShadow=true; environmentRoot.add(patch);
    }
  }

  if(def.id==="industrial-test-track"){
    addBox(environmentRoot,{x:5,y:cfg.platformHeight,z:4},{x:-6,y:cfg.platformHeight/2,z:-3},0x626e73,.6);
    addBox(environmentRoot,{x:3,y:.18,z:5},{x:7,y:.09,z:3},0x9aa3a5,.35);
  }

  if(def.id==="stairs-steps"){
    for(let i=0;i<cfg.stepCount;i++){
      addBox(environmentRoot,{x:cfg.stepWidth,y:cfg.stepHeight*(i+1),z:2},{x:-5+i*cfg.stepWidth,y:cfg.stepHeight*(i+1)/2,z:0},0x7f8987,.75);
    }
  }

  if(def.id==="custom-arena"){
    for(let i=0;i<cfg.challengeCount;i++){
      const x=-6+i*3;
      addBox(environmentRoot,{x:1.2,y:.18+i*.08,z:1.2},{x:x,y:(.18+i*.08)/2,z:i%2?3:-3},i%2?0x7c8b8f:0x5d6d72,.7);
    }
  }

  return def;
}

function renderEnvironmentCards() {
  const grid=document.getElementById("environment-grid");
  const search=document.getElementById("environment-search");
  const category=document.getElementById("environment-category-filter");
  const difficulty=document.getElementById("environment-difficulty-filter");
  if(!grid)return;
  const current=localStorage.getItem("blueprint_selected_environment")||"flat-concrete";
  const query=(search?.value||"").trim().toLowerCase();
  grid.replaceChildren();
  for(const def of environmentDefinitions){
    if(query && !`${def.name} ${def.description} ${def.category} ${def.capabilities.join(" ")}`.toLowerCase().includes(query))continue;
    if(category?.value!=="all" && def.category!==category.value)continue;
    if(difficulty?.value!=="all" && def.difficulty!==difficulty.value)continue;
    const card=document.createElement("article");
    card.className=`environment-card${def.id===current?" selected":""}`;
    card.tabIndex=0;
    card.innerHTML=`
      <img src="./images/environments/${def.id}.webp" alt="${def.name} preview">
      <div class="environment-card-body">
        <h3>${def.name}</h3>
        <p>${def.description}</p>
        <div class="environment-card-meta"><span class="tag">${def.category}</span><span class="difficulty">${def.difficulty}</span></div>
      </div>`;
    const choose=()=>selectEnvironment(def.id,true);
    card.addEventListener("click",choose);
    card.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" ")choose();});
    grid.append(card);
  }
}

function renderEnvironmentDetails(def) {
  document.getElementById("selected-environment-name").textContent=def.name;
  document.getElementById("selected-environment-description").textContent=def.description;
  const img=document.getElementById("selected-environment-image");
  img.src=`./images/environments/${def.id}.webp`;
  img.alt=`${def.name} 3D testing environment preview`;
  document.getElementById("environment-selection-status").textContent=def.name.toUpperCase();
  const tags=document.getElementById("selected-environment-tags");
  tags.replaceChildren(...[def.category,def.difficulty,...def.capabilities].map(text=>{const tag=document.createElement("span");tag.className="tag";tag.textContent=text;return tag;}));
  const config=document.getElementById("environment-config");
  config.replaceChildren();
  const cfg=getConfig(def.id);
  for(const item of def.config){
    const label=document.createElement("label");
    label.textContent=item.label;
    const input=document.createElement("input");
    input.type=item.type==="range"?"range":"number";
    input.min=item.min;input.max=item.max;input.step=item.step;input.value=cfg[item.key];
    input.addEventListener("input",()=>{const stored=envConfig.get(def.id)||{};stored[item.key]=Number(input.value);envConfig.set(def.id,stored);buildEnvironment(def.id);});
    label.append(input);config.append(label);
  }
}

function syncTerrainControls(def) {
  const terrain=document.getElementById("terrain-type");
  if(terrain)terrain.value=def.terrain;
  const slope=document.getElementById("slope-degrees");
  const obstacleHeight=document.getElementById("obstacle-height");
  const obstacleWidth=document.getElementById("obstacle-width");
  if(def.id==="inclined-ramp"&&slope)slope.value=String(getConfig(def.id).slopeAngle);
  if(def.id==="industrial-test-track"&&slope)slope.value=String(getConfig(def.id).rampAngle);
  if(def.config.some(item=>item.key==="obstacleHeight")&&obstacleHeight)obstacleHeight.value=String(getConfig(def.id).obstacleHeight);
  if(obstacleWidth)obstacleWidth.value="0";
}

function selectEnvironment(id, rebuild=true) {
  const def=environmentDefinitions.find(item=>item.id===id)||environmentDefinitions[0];
  localStorage.setItem("blueprint_selected_environment",def.id);
  renderEnvironmentDetails(def);
  renderEnvironmentCards();
  syncTerrainControls(def);
  if(rebuild)buildEnvironment(def.id);
}

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

document.getElementById("environment-search")?.addEventListener("input",renderEnvironmentCards);
document.getElementById("environment-category-filter")?.addEventListener("change",renderEnvironmentCards);
document.getElementById("environment-difficulty-filter")?.addEventListener("change",renderEnvironmentCards);
document.getElementById("load-selected-environment")?.addEventListener("click",()=>{
  const id=localStorage.getItem("blueprint_selected_environment")||"flat-concrete";
  selectEnvironment(id,true);
  fitAssembly();
});

window.BlueprintEnvironmentLibrary={
  environments:environmentDefinitions,
  select:selectEnvironment,
  build:buildEnvironment
};

const initialEnvironment=localStorage.getItem("blueprint_selected_environment")||"flat-concrete";
selectEnvironment(initialEnvironment,true);
renderEnvironmentCards();

loadCatalog();
