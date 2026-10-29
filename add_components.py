"""
Script to append the 6 new components (5 NASA-inspired chassis + 1 RGB light)
to components.py, preserving all existing 21 components.
"""
import re

path = r"D:\BLUEPRINT\components.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Normalise line endings for manipulation, remember what we had
has_crlf = "\r\n" in content
src = content.replace("\r\n", "\n")

NEW_COMPONENTS = '''
    # -------------------- NASA-INSPIRED ROBOT BODIES (Space Library) --------------------
    # These are original conceptual designs inspired by NASA planetary rover programmes.
    # They are NOT replicas of any specific flight-qualified spacecraft or rover.
    # Example mass and dimension values are illustrative only.
    {
        "id": "nasa_mars_rover_body",
        "name": "Mars Rover Body",
        "category": "space",
        "mass_kg": 4.5,
        "description": (
            "Compact, rugged rectangular body inspired by NASA Mars rover designs. "
            "Features equipment panels, wheel-mounting brackets, and thermal shielding. "
            "Original conceptual design — not a replica of any specific NASA vehicle."
        ),
        "tags": ["mars", "rover", "chassis", "body", "NASA", "space", "planetary"],
        "library": "space",
        "spec_status": "example",
        "length_m": 1.5,
        "width_m": 1.2,
        "height_m": 0.6,
        "wheel_mount_count": 6,
        "color_hex": "#8B7355",
    },
    {
        "id": "nasa_lunar_rover_body",
        "name": "Lunar Rover Body",
        "category": "space",
        "mass_kg": 2.8,
        "description": (
            "Low-profile, lightweight body with visible structural framing inspired by "
            "lunar exploration vehicle designs. Open tubular frame for minimal mass. "
            "Original conceptual design — not a replica of any specific NASA vehicle."
        ),
        "tags": ["lunar", "moon", "rover", "chassis", "body", "NASA", "space"],
        "library": "space",
        "spec_status": "example",
        "length_m": 1.2,
        "width_m": 1.0,
        "height_m": 0.45,
        "wheel_mount_count": 4,
        "color_hex": "#D4C5A9",
    },
    {
        "id": "nasa_six_wheel_rover_body",
        "name": "Six-Wheel Science Rover Body",
        "category": "space",
        "mass_kg": 6.0,
        "description": (
            "Robust central chassis with six wheel-mounting points and instrument bays "
            "for scientific payloads, inspired by multi-wheel planetary exploration vehicle designs. "
            "Original conceptual design — not a replica of any specific NASA vehicle."
        ),
        "tags": ["rover", "science", "six-wheel", "chassis", "body", "NASA", "space", "planetary"],
        "library": "space",
        "spec_status": "example",
        "length_m": 1.8,
        "width_m": 1.4,
        "height_m": 0.7,
        "wheel_mount_count": 6,
        "color_hex": "#6B7C8E",
    },
    {
        "id": "nasa_exploration_robot_body",
        "name": "Space Exploration Robot Body",
        "category": "space",
        "mass_kg": 5.2,
        "description": (
            "Modular body with equipment bays, structural panels and antenna-mounting points, "
            "inspired by general space exploration robotics concepts. "
            "Original conceptual design — not a replica of any specific NASA vehicle."
        ),
        "tags": ["exploration", "modular", "robot", "chassis", "body", "NASA", "space", "antenna"],
        "library": "space",
        "spec_status": "example",
        "length_m": 1.6,
        "width_m": 1.1,
        "height_m": 0.8,
        "wheel_mount_count": 4,
        "color_hex": "#7A8B9C",
    },
    {
        "id": "nasa_research_rover_body",
        "name": "Autonomous Research Rover Body",
        "category": "space",
        "mass_kg": 3.5,
        "description": (
            "Compact body with sensor and camera mounting locations and accessible equipment panels, "
            "inspired by autonomous planetary research rover concepts. "
            "Original conceptual design — not a replica of any specific NASA vehicle."
        ),
        "tags": ["autonomous", "research", "rover", "chassis", "body", "NASA", "space", "sensor"],
        "library": "space",
        "spec_status": "example",
        "length_m": 1.1,
        "width_m": 0.9,
        "height_m": 0.55,
        "wheel_mount_count": 4,
        "color_hex": "#8A9B6E",
    },

    # -------------------- RGB LIGHTING --------------------
    # Simulated RGB LED light unit inspired by practical lighting used in space hardware.
    # Labelled as a simulated LED; does not reproduce any specific NASA flight-qualified system.
    {
        "id": "rgb_led_unit",
        "name": "RGB LED Light Unit",
        "category": "electrical",
        "mass_kg": 0.04,
        "description": (
            "Simulated compact RGB LED housing inspired by space-exploration lighting hardware. "
            "Supports red, green, blue and custom colours with adjustable brightness. "
            "This is a simulated LED for visualisation purposes only."
        ),
        "tags": ["rgb", "led", "light", "illumination", "electrical", "space"],
        "library": "space",
        "spec_status": "example",
        "default_color_hex": "#FF0000",
        "brightness": 1.0,
        "powered": True,
    },
'''

# Insert before the closing bracket of COMPONENTS list and get_components()
# Find the position just before the closing `]` of COMPONENTS
marker = '\n]\n\n\ndef get_components():'
replacement = NEW_COMPONENTS + '\n]\n\n\ndef get_components():'

assert marker in src, f"Marker not found in components.py"
src = src.replace(marker, replacement, 1)

final = src.replace("\n", "\r\n") if has_crlf else src
with open(path, "w", encoding="utf-8") as f:
    f.write(final)

print("components.py updated — appended 6 new components.")

