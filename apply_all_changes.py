"""
Apply all NASA chassis + RGB LED changes to the BLUEPRINT project.
Handles CRLF line endings on Windows.
"""
import re, sys

def read(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8")

def write(path, text):
    with open(path, "wb") as f:
        f.write(text.encode("utf-8"))
    print(f"  Written: {path}")

def crlf(text):
    """Normalise all line endings to CRLF."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.replace("\n", "\r\n")

# ──────────────────────────────────────────────────────────────────────────────
# 1. tests/test_backend.py  – update count assertion + add new test function
# ──────────────────────────────────────────────────────────────────────────────
print("=== 1. Patching tests/test_backend.py ===")
path = r"D:\BLUEPRINT\tests\test_backend.py"
text = read(path)

# 1a. Fix count assertion  21 → 27
old = "    # The current unified component library contains 21 items.\r\n    assert len(components) == 21"
new = "    # The current unified component library contains 27 items (21 original + 6 NASA/RGB additions).\r\n    assert len(components) == 27"
if old in text:
    text = text.replace(old, new, 1)
    print("  Fixed: component count assertion 21 to 27")
else:
    # Try LF version
    old_lf = "    # The current unified component library contains 21 items.\n    assert len(components) == 21"
    new_lf = "    # The current unified component library contains 27 items (21 original + 6 NASA/RGB additions).\n    assert len(components) == 27"
    if old_lf in text:
        text = text.replace(old_lf, new_lf, 1)
        print("  Fixed (LF variant): component count assertion 21 to 27")
    else:
        print("  WARNING: count assertion pattern not found — check manually")

# 1b. Append new test function at end of file
new_test = '''

# ============================================================
# NASA-INSPIRED CHASSIS AND RGB LED COMPONENT TESTS
# ============================================================

def test_new_nasa_chassis_and_rgb_components(client):
    """Verify the 6 new NASA-inspired chassis and RGB LED components are present."""
    response = client.get("/api/components")
    assert response.status_code == 200
    components = response.json()["components"]
    ids = {c["id"] for c in components}

    new_ids = [
        "nasa_mars_rover_body",
        "nasa_lunar_rover_body",
        "nasa_six_wheel_rover_body",
        "nasa_exploration_robot_body",
        "nasa_research_rover_body",
        "rgb_led_unit",
    ]
    for nid in new_ids:
        assert nid in ids, f"{nid} missing from component catalogue"

    # Verify key fields for each NASA body
    bodies = {c["id"]: c for c in components if c["id"].startswith("nasa_")}
    assert len(bodies) == 5, f"Expected 5 NASA bodies, found {len(bodies)}"
    for bid, body in bodies.items():
        assert body["category"] == "space", f"{bid}: expected category 'space'"
        assert body["library"] == "space", f"{bid}: expected library 'space'"
        assert body["mass_kg"] > 0, f"{bid}: mass_kg must be > 0"
        assert "wheel_mount_count" in body, f"{bid}: missing wheel_mount_count"
        assert "spec_status" in body, f"{bid}: missing spec_status"
        assert "NASA" in body.get("tags", []), f"{bid}: 'NASA' missing from tags"
        assert "not a replica" in body.get("description", "").lower() or \
               "original conceptual" in body.get("description", "").lower(), \
               f"{bid}: description must contain disclaimer"

    # Verify RGB LED unit
    rgb = next((c for c in components if c["id"] == "rgb_led_unit"), None)
    assert rgb is not None, "rgb_led_unit missing from catalogue"
    assert rgb["category"] == "electrical"
    assert rgb["library"] == "space"
    assert rgb["mass_kg"] == 0.04
    assert "rgb" in rgb["tags"]
    assert rgb["powered"] is True
    assert 0.0 < rgb["brightness"] <= 1.0
    assert "simulated" in rgb.get("description", "").lower(), \
        "rgb_led_unit description must state it is simulated"


def test_nasa_body_fields_have_correct_types(client):
    """Verify numeric and structural fields on NASA bodies have correct Python types."""
    response = client.get("/api/components")
    assert response.status_code == 200
    components = response.json()["components"]
    nasa_bodies = [c for c in components if c["id"].startswith("nasa_")]
    assert len(nasa_bodies) == 5

    for body in nasa_bodies:
        assert isinstance(body["mass_kg"], (int, float)), f"{body['id']} mass_kg type error"
        assert isinstance(body["wheel_mount_count"], int), f"{body['id']} wheel_mount_count type error"
        assert isinstance(body.get("length_m", 0.0), (int, float))
        assert isinstance(body.get("width_m", 0.0), (int, float))
        assert isinstance(body.get("height_m", 0.0), (int, float))
        assert body["mass_kg"] > 0
        assert body["wheel_mount_count"] in (4, 6), f"{body['id']} unexpected wheel count"
'''

# Only append if the test doesn't already exist
if "test_new_nasa_chassis_and_rgb_components" not in text:
    # Strip trailing whitespace/newlines from existing content then add test
    text = text.rstrip() + "\r\n" + crlf(new_test)
    print("  Added: test_new_nasa_chassis_and_rgb_components + test_nasa_body_fields_have_correct_types")
else:
    print("  Skipped: NASA test functions already present")

write(path, text)

# ──────────────────────────────────────────────────────────────────────────────
# 2. frontend/builder.html  – add LED controls panel inside inspector
# ──────────────────────────────────────────────────────────────────────────────
print("\n=== 2. Patching frontend/builder.html ===")
path = r"D:\BLUEPRINT\frontend\builder.html"
text = read(path)

led_html = '''
        <!-- RGB LED Light Unit controls — shown only when an rgb_led_unit is selected -->
        <div id="led-controls" hidden>
          <hr>
          <h3>LED Light Controls</h3>
          <p class="hint">Simulated RGB LED — not a real lighting system.</p>
          <label><input type="checkbox" id="led-power" checked> Power ON</label>
          <div class="led-colours">
            <button type="button" data-led-color="16711680" style="background:#f33;color:#fff">Red</button>
            <button type="button" data-led-color="65280" style="background:#3f3;color:#000">Green</button>
            <button type="button" data-led-color="34815" style="background:#39f;color:#fff">Blue</button>
            <button type="button" data-led-color="16777215" style="background:#fff;color:#000">White</button>
          </div>
          <label>Brightness <input id="led-brightness" type="range" min="0.05" max="1" step="0.05" value="1"></label>
          <label>Custom colour <input id="led-custom-color" type="color" value="#ff0000"></label>
        </div>'''

# Insert after </button> "Remove component" line, inside inspector div
target = '        <button id="remove" type="button">Remove component</button>'
replacement = target + crlf(led_html)

if "led-controls" not in text:
    if target in text:
        text = text.replace(target, replacement, 1)
        print("  Added: #led-controls panel after Remove button")
    else:
        # Try without CRLF
        target_lf = '        <button id="remove" type="button">Remove component</button>'
        if target_lf in text:
            text = text.replace(target_lf, target_lf + "\n" + led_html.replace("\r\n", "\n"), 1)
            print("  Added (LF): #led-controls panel")
        else:
            print("  WARNING: could not find 'Remove component' button in builder.html")
else:
    print("  Skipped: led-controls already present")

write(path, text)

# ──────────────────────────────────────────────────────────────────────────────
# 3. frontend/builder.css  – add LED colour button styles
# ──────────────────────────────────────────────────────────────────────────────
print("\n=== 3. Patching frontend/builder.css ===")
path = r"D:\BLUEPRINT\frontend\builder.css"
text = read(path)

led_css = """
/* ── RGB LED Light Unit controls ─────────────────────────── */
#led-controls {
  margin-top: 8px;
}
#led-controls h3 {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #8ab4f8;
  margin: 8px 0 4px;
}
.led-colours {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin: 8px 0;
}
.led-colours button {
  padding: 5px 10px;
  border-radius: 6px;
  border: 1px solid #344155;
  cursor: pointer;
  font-size: 11px;
  font-weight: 600;
  transition: opacity 0.15s;
}
.led-colours button:hover {
  opacity: 0.82;
}
#led-brightness {
  width: 100%;
  margin-top: 4px;
}
#led-custom-color {
  width: 100%;
  height: 32px;
  padding: 2px;
  border-radius: 4px;
  border: 1px solid #344155;
  background: #1a2233;
  cursor: pointer;
}
"""

if "led-colours" not in text:
    text = text.rstrip() + "\r\n" + crlf(led_css)
    print("  Added: LED control CSS")
else:
    print("  Skipped: LED CSS already present")

write(path, text)

# ──────────────────────────────────────────────────────────────────────────────
# 4. frontend/builder.js  – geometry cases, defaultPos entries, LED JS logic
# ──────────────────────────────────────────────────────────────────────────────
print("\n=== 4. Patching frontend/builder.js ===")
path = r"D:\BLUEPRINT\frontend\builder.js"
text = read(path)

# ── 4a. Geometry switch cases ────────────────────────────────────────────────
geometry_cases = r"""
    // ── NASA-INSPIRED ROBOT BODIES (22-26) ───────────────────────────────────
    // Original conceptual designs inspired by NASA planetary rover programmes.
    // NOT replicas of any specific flight-qualified spacecraft or rover.

    // 22. Mars Rover Body
    case "nasa_mars_rover_body": {
      const roverBody  = mat(0x8B7355, 0.35, 0.75);
      const roverPanel = mat(0x6B5335, 0.4,  0.65);
      const roverMetal = mat(0xA89070, 0.55, 0.5);
      // Main hull
      B(1.5,  0.2,  1.2,  roverBody,  0,    0.6,   0);
      // Top deck with equipment panels
      B(1.3,  0.06, 1.0,  roverPanel, 0,    0.72,  0);
      // Side skirts / thermal panels
      B(0.06, 0.3,  1.2,  roverPanel, -0.78, 0.55, 0);
      B(0.06, 0.3,  1.2,  roverPanel,  0.78, 0.55, 0);
      // Front equipment bay
      B(1.2,  0.18, 0.12, roverPanel, 0,    0.62,  -0.66);
      // Rear thruster bay
      B(0.9,  0.14, 0.1,  roverMetal, 0,    0.62,   0.66);
      // Wheel mount brackets — 3 per side
      for (const side of [-1, 1]) {
        for (const zb of [-0.45, 0, 0.45]) {
          B(0.14, 0.06, 0.12, roverMetal, side * 0.85, 0.48, zb);
        }
      }
      // Top-mounted science mast
      C(0.06,  0.22, roverMetal, 0,    0.86, -0.3, "y");
      B(0.18,  0.06, 0.18, roverPanel, 0,    0.98, -0.3);
      break;
    }

    // 23. Lunar Rover Body
    case "nasa_lunar_rover_body": {
      const lunarGold = mat(0xD4C5A9, 0.4,  0.6);
      const lunarTube = mat(0xB8A88A, 0.55, 0.45);
      // Lower chassis rails (fore-aft)
      B(0.06, 0.06, 1.2,  lunarTube, -0.48, 0.35, 0);
      B(0.06, 0.06, 1.2,  lunarTube,  0.48, 0.35, 0);
      // Cross-members
      for (const zb of [-0.45, 0, 0.45]) {
        B(0.96, 0.06, 0.06, lunarTube, 0, 0.35, zb);
      }
      // Vertical uprights
      for (const xb of [-0.48, 0.48]) {
        for (const zb of [-0.45, 0.45]) {
          B(0.06, 0.36, 0.06, lunarTube, xb, 0.53, zb);
        }
      }
      // Upper frame
      B(0.06, 0.06, 1.0,  lunarTube, -0.48, 0.71, 0);
      B(0.06, 0.06, 1.0,  lunarTube,  0.48, 0.71, 0);
      B(0.96, 0.06, 0.06, lunarTube,  0,    0.71, -0.45);
      B(0.96, 0.06, 0.06, lunarTube,  0,    0.71,  0.45);
      // Instrument platform
      B(0.72, 0.04, 0.5,  lunarGold,  0,    0.58,  0);
      // Wheel brackets — 2 per side
      for (const side of [-1, 1]) {
        for (const zb of [-0.42, 0.42]) {
          B(0.16, 0.05, 0.1, lunarTube, side * 0.56, 0.32, zb);
        }
      }
      break;
    }

    // 24. Six-Wheel Science Rover Body
    case "nasa_six_wheel_rover_body": {
      const sixBody  = mat(0x6B7C8E, 0.4,  0.7);
      const sixPanel = mat(0x4A5B6A, 0.45, 0.65);
      const sixMetal = mat(0x8A9BAE, 0.6,  0.4);
      // Central hull
      B(1.8,  0.24, 1.4,  sixBody,  0,    0.62, 0);
      B(1.6,  0.06, 1.2,  sixPanel, 0,    0.76, 0);
      // Side panel ribs
      for (const zb of [-0.5, 0, 0.5]) {
        B(0.06, 0.24, 0.08, sixMetal, -0.93, 0.62, zb);
        B(0.06, 0.24, 0.08, sixMetal,  0.93, 0.62, zb);
      }
      // Instrument bay (front)
      B(1.4,  0.2,  0.18, sixPanel, 0,    0.64, -0.79);
      // Equipment housing (rear)
      B(1.0,  0.28, 0.2,  sixMetal, 0,    0.66,  0.8);
      // Six wheel mount brackets
      for (const side of [-1, 1]) {
        for (const zb of [-0.55, 0, 0.55]) {
          B(0.18, 0.07, 0.14, sixMetal, side * 1.0, 0.5, zb);
        }
      }
      // Science mast
      C(0.055, 0.35, sixMetal, 0.5,  0.94, -0.5, "y");
      B(0.22,  0.08, 0.16, sixPanel, 0.5,  1.12, -0.5);
      break;
    }

    // 25. Space Exploration Robot Body
    case "nasa_exploration_robot_body": {
      const expBody  = mat(0x7A8B9C, 0.45, 0.6);
      const expPanel = mat(0x5A6B7C, 0.5,  0.55);
      const expWhite = mat(0xDDE8F5, 0.2,  0.55);
      // Core hull
      B(1.6,  0.26, 1.1,  expBody,  0,     0.63, 0);
      // Equipment bays (sides)
      B(0.22, 0.36, 0.7,  expPanel, -0.91, 0.68, 0);
      B(0.22, 0.36, 0.7,  expPanel,  0.91, 0.68, 0);
      // Top module deck
      B(1.3,  0.07, 0.85, expWhite, 0,     0.77, 0);
      // Antenna mount plate (rear top)
      B(0.42, 0.05, 0.38, expPanel, 0,     0.82, 0.42);
      C(0.04, 0.14, expBody,       -0.16,  0.9,  0.42, "y");
      C(0.04, 0.14, expBody,        0.16,  0.9,  0.42, "y");
      // Front sensor bay
      B(1.2,  0.18, 0.12, expPanel, 0,     0.65, -0.62);
      // Wheel mount rails
      for (const side of [-1, 1]) {
        for (const zb of [-0.38, 0.38]) {
          B(0.14, 0.06, 0.12, expBody, side * 1.03, 0.5, zb);
        }
      }
      // Communication array base
      B(0.28, 0.06, 0.28, expPanel, -0.55, 0.8, 0);
      break;
    }

    // 26. Autonomous Research Rover Body
    case "nasa_research_rover_body": {
      const resBody  = mat(0x8A9B6E, 0.35, 0.65);
      const resPanel = mat(0x6A7B4E, 0.4,  0.6);
      const resMetal = mat(0xAABB8E, 0.5,  0.45);
      // Compact main hull
      B(1.1,  0.2,  0.9,  resBody,  0,    0.6,   0);
      B(0.9,  0.05, 0.72, resPanel, 0,    0.72,  0);
      // Side equipment panels
      B(0.05, 0.28, 0.7,  resPanel, -0.58, 0.62, 0);
      B(0.05, 0.28, 0.7,  resPanel,  0.58, 0.62, 0);
      // Camera mast
      C(0.045, 0.4, resMetal, 0,    0.9,  -0.3, "y");
      B(0.2,  0.07, 0.14, resPanel, 0,    1.11, -0.3);
      // Camera housing
      S(0.07, resMetal, 0, 1.15, -0.3);
      // Sensor bar (front)
      B(0.7,  0.07, 0.08, resPanel, 0,    0.64, -0.5);
      C(0.03, 0.05, mat(0x56d8ee, 0.1, 0.3), -0.18, 0.64, -0.55, "z");
      C(0.03, 0.05, mat(0x56d8ee, 0.1, 0.3),  0.18, 0.64, -0.55, "z");
      // Wheel mount brackets
      for (const side of [-1, 1]) {
        for (const zb of [-0.32, 0.32]) {
          B(0.12, 0.05, 0.1, resMetal, side * 0.65, 0.49, zb);
        }
      }
      break;
    }

    // 27. RGB LED Light Unit
    case "rgb_led_unit": {
      // Simulated compact LED housing — NOT a real lighting system.
      const ledOnColor   = part.ledColor    != null ? part.ledColor    : 0xFF0000;
      const ledOn        = part.ledPowered  !== false;
      const ledBright    = part.ledBrightness != null ? part.ledBrightness : 1.0;
      const housingMat = mat(0x2A3040, 0.5, 0.4);
      const lensMat = new THREE.MeshStandardMaterial({
        color:            ledOn ? ledOnColor : 0x222222,
        emissive:         ledOn ? new THREE.Color(ledOnColor) : new THREE.Color(0x000000),
        emissiveIntensity: ledOn ? ledBright * 1.5 : 0,
        metalness:  0.1,
        roughness:  0.1,
        transparent: true,
        opacity:    0.92,
      });
      const ringMat = mat(0x9AACBB, 0.7, 0.25);
      // Housing block
      B(0.28, 0.14, 0.22, housingMat, 0, 0.52, 0);
      // LED lens dome
      S(0.07, lensMat, 0, 0.6, -0.06);
      // Mounting ring
      C(0.1,  0.025, ringMat, 0, 0.59, -0.06, "z", 24);
      // Heat sink fins
      for (let fi = 0; fi < 4; fi++) {
        B(0.025, 0.09, 0.02, ringMat, (fi - 1.5) * 0.065, 0.51, 0.12);
      }
      // Connector pins
      C(0.015, 0.065, mat(0xdcae48, 0.65, 0.3), -0.07, 0.45, 0.11, "y");
      C(0.015, 0.065, mat(0xdcae48, 0.65, 0.3),  0.07, 0.45, 0.11, "y");
      // Point light — only when powered on
      if (ledOn) {
        const ptLight = new THREE.PointLight(ledOnColor, ledBright * 1.8, 3.5, 2);
        ptLight.position.set(0, 0.65, -0.08);
        ptLight.castShadow = false;
        group.add(ptLight);
        group.userData.rgbPointLight = ptLight;
      }
      group.userData.isRgbLed = true;
      break;
    }

"""

fallback_marker = "    // 21. Safe fallback for future or unrecognized component IDs"

if "nasa_mars_rover_body" not in text:
    if fallback_marker in text:
        text = text.replace(fallback_marker, crlf(geometry_cases) + fallback_marker, 1)
        print("  Added: 6 geometry switch cases (22-27)")
    else:
        print("  WARNING: fallback_marker not found in builder.js — check manually")
else:
    print("  Skipped: NASA geometry cases already present")

# ── 4b. defaultPos entries ─────────────────────────────────────────────────
default_pos_insert = """
  // NASA-inspired rover bodies — start at origin so they sit centered.
  if (
    id === "nasa_mars_rover_body" ||
    id === "nasa_six_wheel_rover_body" ||
    id === "nasa_exploration_robot_body" ||
    id === "nasa_lunar_rover_body" ||
    id === "nasa_research_rover_body"
  ) {
    return { x: 0, y: 0, z: 0 };
  }

  // RGB LED Light Unit — mount near top corners of the assembly.
  if (id === "rgb_led_unit") {
    const ledCount = parts.filter(p => p.componentId === "rgb_led_unit").length;
    const offsets = [
      { x:  0.55, y: 0.55, z: -0.5 },
      { x: -0.55, y: 0.55, z: -0.5 },
      { x:  0.55, y: 0.55, z:  0.5 },
      { x: -0.55, y: 0.55, z:  0.5 },
    ];
    return offsets[ledCount % offsets.length];
  }

"""

fallback_pos_marker = "  // Fallback for unknown components."

if "nasa_mars_rover_body" not in text or "rgb_led_unit" not in text.split("defaultPos")[1].split("}")[0]:
    if fallback_pos_marker in text:
        text = text.replace(fallback_pos_marker, crlf(default_pos_insert) + fallback_pos_marker, 1)
        print("  Added: defaultPos entries for NASA bodies and RGB LED")
    else:
        print("  WARNING: fallback_pos_marker not found — check manually")
else:
    print("  Skipped: defaultPos entries already present")

# ── 4c. RGB LED rebuild function + writeInspector LED controls ─────────────
led_js_functions = """

// ── RGB LED Light Unit helpers ─────────────────────────────────────────────

/**
 * Dispose and rebuild geometry for an rgb_led_unit part so colour/brightness
 * changes are reflected immediately in the scene.
 */
function rebuildLedGeometry(part) {
  if (!part || !part.group) return;
  // Remove all existing children (meshes, lights).
  while (part.group.children.length > 0) {
    const child = part.group.children[0];
    if (child.geometry) child.geometry.dispose();
    if (child.material) {
      const mats = Array.isArray(child.material) ? child.material : [child.material];
      mats.forEach(m => m.dispose());
    }
    part.group.remove(child);
  }
  // Rebuild geometry using the part's current ledColor/ledPowered/ledBrightness.
  const newGroup = geometry(part);
  while (newGroup.children.length > 0) {
    part.group.add(newGroup.children[0]);
  }
  render();
}

/**
 * Apply LED state update: set property, rebuild geometry, refresh inspector.
 */
function applyLedUpdate() {
  if (!selected || selected.componentId !== "rgb_led_unit") return;

  const powerEl      = $("led-power");
  const brightnessEl = $("led-brightness");
  const customEl     = $("led-custom-color");

  if (powerEl)      selected.ledPowered    = powerEl.checked;
  if (brightnessEl) selected.ledBrightness = parseFloat(brightnessEl.value) || 1.0;

  rebuildLedGeometry(selected);
}

/**
 * Wire up the LED control panel events once (idempotent via data attribute).
 */
function setupLedControls() {
  const container = $("led-controls");
  if (!container || container.dataset.wired) return;
  container.dataset.wired = "1";

  const powerEl      = $("led-power");
  const brightnessEl = $("led-brightness");
  const customEl     = $("led-custom-color");

  if (powerEl)      powerEl.addEventListener("change", applyLedUpdate);
  if (brightnessEl) brightnessEl.addEventListener("input",  applyLedUpdate);

  // Colour preset buttons
  container.querySelectorAll("[data-led-color]").forEach(btn => {
    btn.addEventListener("click", () => {
      if (!selected || selected.componentId !== "rgb_led_unit") return;
      selected.ledColor = parseInt(btn.dataset.ledColor, 10);
      // Sync custom colour picker
      if (customEl) {
        customEl.value = "#" + selected.ledColor.toString(16).padStart(6, "0");
      }
      applyLedUpdate();
    });
  });

  if (customEl) {
    customEl.addEventListener("input", () => {
      if (!selected || selected.componentId !== "rgb_led_unit") return;
      selected.ledColor = parseInt(customEl.value.replace("#", ""), 16);
      applyLedUpdate();
    });
  }
}

"""

if "rebuildLedGeometry" not in text:
    # Insert before the EXPECTED_IDS block
    expected_ids_marker = "// Report missing HTML elements once instead of failing later."
    if expected_ids_marker in text:
        text = text.replace(expected_ids_marker, crlf(led_js_functions) + expected_ids_marker, 1)
        print("  Added: rebuildLedGeometry, applyLedUpdate, setupLedControls functions")
    else:
        print("  WARNING: EXPECTED_IDS marker not found — appending LED functions to end")
        text = text.rstrip() + "\r\n" + crlf(led_js_functions)
else:
    print("  Skipped: LED JS functions already present")

# ── 4d. Patch writeInspector to show/hide #led-controls ──────────────────
led_inspector_patch = """
  // Show or hide the RGB LED control panel.
  const ledControlsEl = $("led-controls");
  if (ledControlsEl) {
    const isLed = selected && selected.componentId === "rgb_led_unit";
    ledControlsEl.hidden = !isLed;
    if (isLed) {
      setupLedControls();
      const powerEl      = $("led-power");
      const brightnessEl = $("led-brightness");
      const customEl     = $("led-custom-color");
      if (powerEl)      powerEl.checked = selected.ledPowered !== false;
      if (brightnessEl) brightnessEl.value = selected.ledBrightness != null ? selected.ledBrightness : 1.0;
      if (customEl && selected.ledColor != null) {
        customEl.value = "#" + selected.ledColor.toString(16).padStart(6, "0");
      }
    }
  }
"""

# Find end of writeInspector: the closing brace right after scaleInput block
write_inspector_end = "  const scaleInput = $(\"scale\");\r\n  if (scaleInput) scaleInput.placeholder = uniform ? \"\" : \"mixed\";\r\n}"
write_inspector_end_lf = "  const scaleInput = $(\"scale\");\n  if (scaleInput) scaleInput.placeholder = uniform ? \"\" : \"mixed\";\n}"

if "ledControlsEl" not in text:
    if write_inspector_end in text:
        text = text.replace(
            write_inspector_end,
            write_inspector_end[:-1] + crlf(led_inspector_patch) + "}",
            1
        )
        print("  Added: LED inspector sync in writeInspector()")
    elif write_inspector_end_lf in text:
        text = text.replace(
            write_inspector_end_lf,
            write_inspector_end_lf[:-1] + "\n" + led_inspector_patch.replace("\r\n", "\n") + "}",
            1
        )
        print("  Added (LF): LED inspector sync in writeInspector()")
    else:
        print("  WARNING: writeInspector end pattern not found — LED inspector not patched")
else:
    print("  Skipped: LED inspector sync already present")

# ── 4e. Hide led-controls when select(null) is called ────────────────────
select_null_patch = """
  // Hide LED controls when no part is selected.
  const ledPanel = $("led-controls");
  if (ledPanel) ledPanel.hidden = true;
"""

select_null_marker = "  setHidden(\"empty\", !!selected);\r\n  setHidden(\"inspector\", !selected);"
select_null_marker_lf = "  setHidden(\"empty\", !!selected);\n  setHidden(\"inspector\", !selected);"

if "led-controls" not in text.split("function select")[1].split("function writeInspector")[0]:
    if select_null_marker in text:
        text = text.replace(
            select_null_marker,
            select_null_marker + "\r\n" + crlf(select_null_patch),
            1
        )
        print("  Added: hide led-controls in select()")
    elif select_null_marker_lf in text:
        text = text.replace(
            select_null_marker_lf,
            select_null_marker_lf + "\n" + select_null_patch.replace("\r\n", "\n"),
            1
        )
        print("  Added (LF): hide led-controls in select()")
    else:
        print("  WARNING: select() null marker not found — led-controls not hidden on deselect")
else:
    print("  Skipped: led-controls hide already in select()")

# ── 4f. Add led-controls to EXPECTED_IDS ─────────────────────────────────
old_expected = '  "sim-status", "sim-state", "sim-time", "sim-detail",'
new_expected = '  "sim-status", "sim-state", "sim-time", "sim-detail",\r\n  "led-controls", "led-power", "led-brightness", "led-custom-color",'

if "led-controls" not in text.split("EXPECTED_IDS")[1].split("];")[0]:
    if old_expected in text:
        text = text.replace(old_expected, new_expected, 1)
        print("  Added: led-controls etc. to EXPECTED_IDS")
    else:
        print("  WARNING: EXPECTED_IDS pattern not found — led-controls not added to array")
else:
    print("  Skipped: led-controls already in EXPECTED_IDS")

write(path, text)

print("\n=== All patches applied. ===")
print("Now run: & D:\\BLUEPRINT\\.venv\\Scripts\\python -m pytest -v")
