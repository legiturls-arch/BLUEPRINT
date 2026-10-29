
# BLUEPRINT Engineering Component Catalogue
# The original five component IDs and core specifications are preserved.

COMPONENTS = [
    # -------------------- ORIGINAL COMPONENTS --------------------
    {
    "id": "motor_basic",
    "name": "Basic DC Motor",
    "category": "actuator",
    "mass_kg": 0.2,

    # Existing prototype value; not a verified datasheet value
    "max_torque_nm": 0.5,

    # Datasheet fields: unknown until a specific motor is selected
    "rated_voltage_v": None,
    "no_load_rpm": None,
    "stall_torque_nm": None,
    "rated_current_a": None,
    "gear_ratio": None,

"description": "Starter motor for a small robot.",
    
    "tags": ["motor", "dc", "robotics"],
    "library": "engineering",
    "spec_status": "prototype"
,},
    {
        "id": "wheel_basic",
        "name": "Basic Wheel",
        "category": "mechanical",
        "mass_kg": 0.15,
        "radius_m": 0.05,
        "description": "Starter wheel for a mobile robot.",
        "tags": ["wheel", "rover", "mobility"],
        "library": "engineering",
        "spec_status": "prototype"
    },
    {
        "id": "battery_basic",
        "name": "Basic Battery",
        "category": "power",
        "mass_kg": 0.3,
        "voltage_v": 12.0,
        "description": "Prototype 12 V power source.",
        "tags": ["battery", "power", "electrical"],
        "library": "engineering",
        "spec_status": "prototype"
    },
    {
        "id": "chassis_basic",
        "name": "Basic Chassis",
        "category": "structure",
        "mass_kg": 1.0,
        "description": "Base structure for a mobile robot.",
        "tags": ["chassis", "frame", "robot"],
        "library": "engineering",
        "spec_status": "prototype"
    },
    {
        "id": "sensor_basic",
        "name": "Distance Sensor",
        "category": "sensor",
        "mass_kg": 0.05,
        "range_m": 2.0,
        "description": "Prototype sensor for measuring distance.",
        "tags": ["distance", "sensor", "ultrasonic"],
        "library": "engineering",
        "spec_status": "prototype"
    },

    # -------------------- MOTORS AND ACTUATORS --------------------
    {
        "id": "motor_geared",
        "name": "Geared DC Motor",
        "category": "actuator",
        "mass_kg": 0.25,
        "max_torque_nm": 1.0,
        "rated_voltage_v": 12.0,
        "no_load_rpm": 200.0,
        "stall_torque_nm": 1.0,
        "gear_ratio": 5.0,
        "description": "Example geared motor for a small robot.",
        "tags": ["gear motor", "dc", "robotics"],
        "library": "engineering",
        "spec_status": "verified"
    },
    {
        "id": "servo_basic",
        "name": "Servo Motor",
        "category": "actuator",
        "mass_kg": 0.06,
        "description": "Example actuator for controlled angular movement.",
        "tags": ["servo", "position", "robotics"],
        "library": "engineering",
        "spec_status": "example"
    },
    {
        "id": "stepper_basic",
        "name": "Stepper Motor",
        "category": "actuator",
        "mass_kg": 0.2,
        "description": "Example motor for step-based positioning.",
        "tags": ["stepper", "positioning", "automation"],
        "library": "engineering",
        "spec_status": "example"
    },

    # -------------------- SENSORS --------------------
    {
        "id": "sensor_temperature",
        "name": "Temperature Sensor",
        "category": "sensor",
        "mass_kg": 0.02,
        "description": "Example sensor for temperature measurement.",
        "tags": ["temperature", "thermal", "environment"],
        "library": "engineering",
        "spec_status": "example"
    },
    {
        "id": "sensor_imu",
        "name": "IMU Sensor",
        "category": "sensor",
        "mass_kg": 0.03,
        "description": "Measures motion-related quantities such as acceleration and rotation.",
        "tags": ["imu", "gyroscope", "accelerometer"],
        "library": "engineering",
        "spec_status": "example"
    },
    {
        "id": "sensor_light",
        "name": "Light Sensor",
        "category": "sensor",
        "mass_kg": 0.02,
        "description": "Example sensor for measuring light intensity.",
        "tags": ["light", "optical", "environment"],
        "library": "engineering",
        "spec_status": "example"
    },

    # -------------------- MECHANICAL AND STRUCTURE --------------------
    {
        "id": "gear_basic",
        "name": "Basic Gear",
        "category": "mechanical",
        "mass_kg": 0.08,
        "description": "Placeholder gear for a mechanical assembly.",
        "tags": ["gear", "transmission", "mechanical"],
        "library": "engineering",
        "spec_status": "example"
    },
    {
        "id": "frame_basic",
        "name": "Structural Frame",
        "category": "structure",
        "mass_kg": 0.5,
        "description": "Example frame for supporting components.",
        "tags": ["frame", "structure", "support"],
        "library": "engineering",
        "spec_status": "example"
    },

    # -------------------- ELECTRICAL --------------------
    {
        "id": "controller_basic",
        "name": "Robot Controller",
        "category": "electrical",
        "mass_kg": 0.05,
        "description": "Placeholder controller for robot logic.",
        "tags": ["controller", "microcontroller", "electronics"],
        "library": "engineering",
        "spec_status": "example"
    },
    {
        "id": "power_converter",
        "name": "Power Converter",
        "category": "electrical",
        "mass_kg": 0.08,
        "description": "Placeholder component for voltage conversion.",
        "tags": ["converter", "voltage", "power"],
        "library": "engineering",
        "spec_status": "example"
    },

    # -------------------- SPACE ENGINEERING LIBRARY --------------------
    # These are conceptual learning components, not official flight hardware.
    # Do not treat example values as real NASA, ISRO or SpaceX specifications.
    {
        "id": "space_rover_wheel",
        "name": "Planetary Rover Wheel",
        "category": "space",
        "mass_kg": 0.5,
        "description": "Conceptual wheel for a planetary rover assembly.",
        "tags": ["rover", "planetary", "NASA", "ISRO", "mobility"],
        "library": "space",
        "spec_status": "example"
    },
    {
        "id": "space_solar_panel",
        "name": "Spacecraft Solar Panel",
        "category": "power",
        "mass_kg": 0.8,
        "description": "Conceptual solar array for a spacecraft.",
        "tags": ["solar", "spacecraft", "NASA", "ISRO", "power"],
        "library": "space",
        "spec_status": "example"
    },
    {
        "id": "space_antenna",
        "name": "Space Communication Antenna",
        "category": "electrical",
        "mass_kg": 0.2,
        "description": "Conceptual antenna for spacecraft communication.",
        "tags": ["antenna", "communication", "satellite", "ISRO"],
        "library": "space",
        "spec_status": "example"
    },
    {
        "id": "space_sensor",
        "name": "Planetary Science Sensor",
        "category": "sensor",
        "mass_kg": 0.15,
        "description": "Conceptual sensor payload for planetary exploration.",
        "tags": ["science", "planetary", "NASA", "ISRO", "payload"],
        "library": "space",
        "spec_status": "example"
    },
    {
        "id": "space_thruster",
        "name": "Spacecraft Thruster",
        "category": "actuator",
        "mass_kg": 0.4,
        "description": "Conceptual propulsion component for spacecraft orientation.",
        "tags": ["thruster", "propulsion", "SpaceX", "spacecraft"],
        "library": "space",
        "spec_status": "example"
    },
    {
        "id": "space_payload_frame",
        "name": "Satellite Payload Frame",
        "category": "structure",
        "mass_kg": 1.0,
        "description": "Conceptual structure for mounting spacecraft payloads.",
        "tags": ["satellite", "payload", "structure", "NASA", "ISRO"],
        "library": "space",
        "spec_status": "example"
    },
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

]


def get_components():
    """Return the component catalogue used by the API."""
    return COMPONENTS
