
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

    # -------------------- EMBEDDED COMPONENTS --------------------
    {
        "id": "controller_esp32",
        "name": "ESP32 Development Board",
        "category": "electrical",
        "mass_kg": 0.015,
        "dimensions_mm": {"length": 55, "width": 28, "height": 8},
        "operating_voltage_v": 3.3,
        "supply_voltage_max_v": 5.0,
        "cpu_cores": 2,
        "clock_frequency_mhz": 240.0,
        "flash_memory_mb": 4.0,
        "sram_kb": 520.0,
        "gpio_count": 34,
        "adc_channels": 18,
        "adc_resolution_bits": 12,
        "pwm_channels": 16,
        "pwm_frequency_hz": 5000.0,
        "current_draw_active_ma": 80.0,
        "current_draw_wifi_tx_ma": 240.0,
        "current_draw_sleep_ma": 0.8,
        "wireless_protocols": ["Wi-Fi 802.11 b/g/n", "Bluetooth LE / Classic"],
        "description": "A USB-powered ESP32-WROOM-32 development board for embedded control and wireless IoT projects. The module integrates a dual-core microcontroller, 2.4 GHz radio, and PCB antenna; board pin availability varies by revision.",
        "working_principle": "The ESP32 executes firmware on its microcontroller cores. GPIO peripherals sample digital levels or drive outputs; the LEDC peripheral produces hardware PWM; UART peripherals exchange asynchronous serial bytes. Wi-Fi and Bluetooth are integrated in the SoC.",
        "technical_specifications": {
            "Typical board size": "55 x 28 mm; varies by DevKit revision",
            "Logic voltage": "3.3 V; GPIOs are not 5 V tolerant",
            "USB input": "5 V through the board regulator",
            "Processor": "Dual-core Xtensa LX6, up to 240 MHz (ESP32-WROOM-32 variant)",
            "Memory": "Typically 4 MB flash; 520 KB SRAM in the ESP32 SoC",
            "Peripherals": "Digital GPIO, 12-bit ADC, LEDC PWM, UART, SPI, I2C",
            "Wireless": "2.4 GHz Wi-Fi and Bluetooth; exact support depends on ESP32 variant",
        },
        "pin_configuration": [
            {"pin": "3V3 / GND", "function": "Regulated 3.3 V output and common ground."},
            {"pin": "5V / VIN", "function": "Board power input from USB or a supported 5 V source; verify board revision."},
            {"pin": "GPIO0 (BOOT)", "function": "Boot-mode strap; hold LOW during reset to enter download mode."},
            {"pin": "EN", "function": "Chip enable/reset; pulling LOW resets the ESP32."},
            {"pin": "GPIO1 / GPIO3", "function": "UART0 TX / RX, commonly connected to the USB serial bridge."},
            {"pin": "GPIO16 / GPIO17", "function": "Common UART2 RX / TX choices; pin mapping is configurable."},
            {"pin": "GPIO18 / GPIO19 / GPIO23", "function": "Common SPI signals; mappings are configurable."},
            {"pin": "GPIO21 / GPIO22", "function": "Common I2C SDA / SCL choices; mappings are configurable."},
            {"pin": "GPIO34-GPIO39", "function": "Input-only GPIOs on the classic ESP32; several support ADC input."},
        ],
        "inputs": ["3.3 V-compatible digital GPIO levels", "ADC voltages within the configured input range", "UART serial data", "Firmware and wireless network data"],
        "outputs": ["3.3 V digital GPIO levels", "LEDC PWM signals", "UART serial data", "Wi-Fi and Bluetooth transmissions"],
        "applications": ["IoT sensor nodes", "Robot control", "Wireless telemetry", "Embedded prototyping"],
        "working_algorithm": [
            "Initialize the required GPIO directions and UART baud rate; configure ADC and PWM peripherals as needed.",
            "Read digital inputs with digitalRead() and analog inputs with analogRead() using an allowed input voltage.",
            "Set digital outputs with digitalWrite(); generate PWM by writing a duty value to an LEDC channel.",
            "Exchange bytes asynchronously over UART and parse complete messages in firmware.",
            "Repeat input, decision, output, and communication work in the main loop or scheduled tasks.",
        ],
        "example_code": "constexpr int INPUT_PIN = 4;\nconstexpr int PWM_PIN = 18;\nconstexpr int UART_RX = 16;\nconstexpr int UART_TX = 17;\n\nvoid setup() {\n  pinMode(INPUT_PIN, INPUT_PULLUP);\n  pinMode(2, OUTPUT);\n  Serial.begin(115200);\n  Serial1.begin(9600, SERIAL_8N1, UART_RX, UART_TX);\n  ledcAttach(PWM_PIN, 5000, 8);  // Arduino-ESP32 3.x\n}\n\nvoid loop() {\n  digitalWrite(2, digitalRead(INPUT_PIN) == LOW);\n  ledcWrite(PWM_PIN, 128);       // 50% duty at 8-bit resolution\n  while (Serial1.available()) Serial.write(Serial1.read());\n  delay(10);\n}",
        "tags": ["controller", "esp32", "microcontroller", "wireless", "wifi", "bluetooth", "iot", "electrical"],
        "aliases": ["esp32", "esp32_controller", "esp32_devkit"],
        "library": "engineering",
        "spec_status": "example",
        "specification_note": "Representative ESP32-WROOM-32 DevKit values; pinout, dimensions, and current vary by board revision and workload.",
    },
    {
        "id": "sensor_ir",
        "name": "IR Obstacle Detection Sensor",
        "category": "sensor",
        "mass_kg": 0.008,
        "dimensions_mm": {"length": 32, "width": 14, "height": 12},
        "operating_voltage_v": 5.0,
        "supply_voltage_min_v": 3.3,
        "supply_voltage_max_v": 5.0,
        "current_draw_ma": 20.0,
        "min_range_m": 0.02,
        "max_range_m": 0.30,
        "beam_angle_deg": 15.0,
        "response_time_ms": 20.0,
        "output_type": "digital",
        "description": "An adjustable reflective infrared obstacle sensor board with an IR emitter, photodetector, LM393 comparator, and sensitivity trimmer. Detection distance depends strongly on target reflectivity, angle, ambient light, and module revision.",
        "working_principle": "The IR LED illuminates the area in front of the board. A nearby surface reflects some of that light to the photodetector. The LM393 compares the detector signal with the trimmer-set threshold and switches the digital output when the threshold is crossed.",
        "technical_specifications": {
            "Typical board size": "32 x 14 mm; varies by module",
            "Supply": "Common boards accept 3.3-5 V; check the specific board",
            "Emitter": "Infrared LED, typically near 940 nm",
            "Detection distance": "Often adjustable over roughly 2-30 cm; surface dependent",
            "Comparator": "LM393; threshold set by onboard potentiometer",
            "Output": "Digital comparator output; commonly active LOW on detection",
        },
        "pin_configuration": [
            {"pin": "VCC", "function": "Module supply; use the voltage range supported by the board."},
            {"pin": "GND", "function": "Common ground with the controller."},
            {"pin": "OUT / DO", "function": "Comparator logic output; usually LOW when reflected IR exceeds the threshold."},
        ],
        "inputs": ["Supply voltage", "Reflected infrared light from a target", "Sensitivity threshold set by the potentiometer"],
        "outputs": ["Digital obstacle-detection level at OUT"],
        "applications": ["Robot obstacle detection", "Object counters", "Short-range presence sensing", "Line-sensing demonstrations"],
        "working_algorithm": [
            "Drive the IR emitter to illuminate the target area.",
            "Collect target-reflected IR at the photodetector; received signal varies with distance, angle, surface, and ambient light.",
            "Condition the detector signal and compare it with the potentiometer-set reference in the LM393.",
            "Switch OUT when the comparator threshold is crossed; on common boards detection is active LOW.",
            "Read OUT as a digital input and apply application-level filtering or debounce if needed.",
        ],
        "example_code": "constexpr int IR_OUT = 27;\n\nvoid setup() {\n  Serial.begin(115200);\n  pinMode(IR_OUT, INPUT);\n}\n\nvoid loop() {\n  const bool detected = (digitalRead(IR_OUT) == LOW);\n  Serial.println(detected ? \"Obstacle detected\" : \"Clear\");\n  delay(50);\n}",
        "tags": ["sensor", "ir", "infrared", "obstacle", "proximity", "robotics"],
        "aliases": ["ir_sensor", "sensor_ir_obstacle", "ir_proximity_sensor"],
        "library": "engineering",
        "spec_status": "example",
        "specification_note": "Range and output polarity are module-dependent; adjust the trimmer and verify the board documentation.",
    },
    {
        "id": "sensor_ir_receiver",
        "name": "IR Receiver Module",
        "category": "sensor",
        "mass_kg": 0.005,
        "dimensions_mm": {"length": 15, "width": 13, "height": 12},
        "operating_voltage_v": 3.3,
        "supply_voltage_min_v": 2.7,
        "supply_voltage_max_v": 5.5,
        "current_draw_ma": 1.5,
        "carrier_frequency_khz": 38.0,
        "supported_protocol": "NEC (common; protocol is decoded by host firmware)",
        "description": "A small three-pin 38 kHz demodulating infrared receiver module. Its black optical package contains a photodetector, amplifier, band-pass filtering, and demodulation circuitry; it outputs a logic pulse train rather than raw photodiode data.",
        "working_principle": "The optical sensor detects modulated infrared bursts. Internal filtering and automatic gain control reject much ambient light, then the demodulator removes the 38 kHz carrier and presents the encoded envelope as active-LOW digital pulses for a microcontroller to decode.",
        "technical_specifications": {
            "Typical board size": "About 15 x 13 mm; varies by breakout",
            "Supply": "Common receiver devices operate around 2.7-5.5 V; check the part marking",
            "Carrier": "38 kHz nominal for the common variant",
            "Output": "Demodulated active-LOW pulse output",
            "Protocol": "NEC timing can be decoded in firmware; other remotes may use other protocols",
        },
        "pin_configuration": [
            {"pin": "OUT", "function": "Demodulated logic pulses; polarity and pin order depend on the receiver."},
            {"pin": "GND", "function": "Common ground."},
            {"pin": "VCC", "function": "Regulated module supply within the receiver's rated range."},
        ],
        "inputs": ["38 kHz-modulated infrared light", "Module supply voltage"],
        "outputs": ["Active-LOW demodulated pulse train for the host decoder"],
        "applications": ["Infrared remote controls", "Appliance control", "Short-range optical commands", "Teaching NEC pulse-distance decoding"],
        "working_algorithm": [
            "Detect incoming IR bursts and select energy near the receiver's nominal 38 kHz carrier.",
            "Amplify and filter the signal; automatic gain control limits slowly varying ambient-light interference.",
            "Demodulate the carrier and output active-LOW envelope pulses.",
            "Measure pulse and space durations in firmware; for NEC, recognize the 9 ms mark and 4.5 ms space leader.",
            "Decode 32 pulse-distance bits (560 us mark; approximately 560 us space for 0 or 1690 us for 1), then validate address and command complements before accepting the frame.",
        ],
        "example_code": "#include <IRremote.hpp>\n\nconstexpr uint8_t IR_PIN = 27;\n\nvoid setup() {\n  Serial.begin(115200);\n  IrReceiver.begin(IR_PIN, DISABLE_LED_FEEDBACK);\n}\n\nvoid loop() {\n  if (IrReceiver.decode()) {\n    if (IrReceiver.decodedIRData.protocol == NEC) {\n      Serial.printf(\"Address: 0x%04X Command: 0x%02X\\n\",\n                    IrReceiver.decodedIRData.address,\n                    IrReceiver.decodedIRData.command);\n    }\n    IrReceiver.resume();\n  }\n}",
        "tags": ["sensor", "ir", "infrared", "receiver", "remote", "nec", "demodulator"],
        "aliases": ["ir_receiver", "tsop38238", "ir_demodulator"],
        "library": "engineering",
        "spec_status": "example",
        "specification_note": "Pin order and rated supply depend on the marked receiver and breakout; confirm before wiring.",
    },
    {
        "id": "motor_driver_l298n",
        "name": "L298N Motor Driver",
        "category": "electrical",
        "mass_kg": 0.035,
        "dimensions_mm": {"length": 43, "width": 43, "height": 28},
        "logic_voltage_v": 5.0,
        "motor_voltage_min_v": 4.5,
        "motor_voltage_max_v": 35.0,
        "continuous_current_a": 2.0,
        "channels": 2,
        "saturation_voltage_drop_v": 1.8,
        "max_pwm_frequency_khz": 25.0,
        "description": "A common red breakout board around the L298N dual bipolar H-bridge IC. It switches motor polarity for two brushed DC motors and accepts PWM on ENA/ENB; the heatsink and board regulator/jumpers vary by clone.",
        "working_principle": "Each H-bridge drives one motor by switching the polarity across its terminals. IN1/IN2 and IN3/IN4 select each bridge state; ENA/ENB enable a bridge and can receive PWM for speed control. The bipolar output stage has a substantial load-dependent voltage drop and dissipates heat.",
        "technical_specifications": {
            "Typical board size": "About 43 x 43 mm; clone layouts vary",
            "Motor supply (VS)": "Common board range 5-35 V; follow the specific board and IC limits",
            "Logic supply (VSS)": "5 V for the L298N logic",
            "Output stages": "Two full H-bridges; nominally up to 2 A per channel with adequate thermal design",
            "Voltage drop": "Bipolar bridge drop is significant and rises with load current",
            "PWM": "Apply PWM to ENA/ENB; use a suitable frequency and remove enable jumpers if required by the board",
        },
        "pin_configuration": [
            {"pin": "ENA / ENB", "function": "Bridge enables; apply PWM here for motor speed control when jumpers are removed."},
            {"pin": "IN1 / IN2", "function": "Direction inputs for motor channel A."},
            {"pin": "IN3 / IN4", "function": "Direction inputs for motor channel B."},
            {"pin": "OUT1 / OUT2", "function": "Motor A terminals."},
            {"pin": "OUT3 / OUT4", "function": "Motor B terminals."},
            {"pin": "+12V / VS", "function": "Motor supply input; terminal label is board-dependent."},
            {"pin": "+5V / VSS", "function": "Logic supply or board regulator output; check the onboard jumper and board documentation."},
            {"pin": "GND", "function": "Common ground for motor supply and controller logic."},
        ],
        "inputs": ["Logic levels on IN1-IN4", "PWM/enable levels on ENA and ENB", "Motor supply VS and logic supply VSS"],
        "outputs": ["Switched motor-terminal polarity and PWM voltage at OUT1-OUT4", "Motor current through each H-bridge"],
        "applications": ["Two-motor robot drive", "Brushed DC motor direction control", "Stepper motor experiments within driver ratings"],
        "working_algorithm": [
            "Connect motor supply, logic supply, and controller ground according to the particular board; never power motors from GPIO pins.",
            "For each bridge, set its IN pair to (1,0) for one direction or (0,1) for the opposite direction.",
            "Apply PWM to ENA or ENB to vary average motor voltage and speed; account for the L298N voltage drop and heating.",
            "Use (0,0) for a coasting bridge and (1,1) for dynamic braking when enabled; disable EN for a high-impedance coast.",
            "Keep current and temperature within the board's thermal limits; add flyback protection if it is not already provided.",
        ],
        "example_code": "constexpr int ENA = 5;\nconstexpr int IN1 = 7;\nconstexpr int IN2 = 8;\n\nvoid setup() {\n  pinMode(ENA, OUTPUT);\n  pinMode(IN1, OUTPUT);\n  pinMode(IN2, OUTPUT);\n}\n\nvoid loop() {\n  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);  // forward\n  analogWrite(ENA, 180);  // 8-bit PWM speed\n  delay(2000);\n  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH); // reverse\n  delay(2000);\n  analogWrite(ENA, 0);    // disable / coast\n}",
        "tags": ["motor_driver", "driver", "h_bridge", "l298n", "actuator", "electrical", "motor_control"],
        "aliases": ["motor_driver", "l298n", "h_bridge_driver"],
        "library": "engineering",
        "spec_status": "example",
        "specification_note": "Board layouts, regulator jumpers, thermal performance, and current capability vary among L298N modules.",
    },
    {
        "id": "sensor_gps_neo6m",
        "name": "NEO-6M GPS Module",
        "category": "sensor",
        "mass_kg": 0.018,
        "dimensions_mm": {"length": 35, "width": 25, "height": 8},
        "operating_voltage_v": 3.3,
        "supply_voltage_max_v": 5.0,
        "current_draw_ma": 45.0,
        "channels": 50,
        "update_rate_hz": 5.0,
        "horizontal_accuracy_m": 2.5,
        "velocity_accuracy_ms": 0.1,
        "ttff_cold_s": 27.0,
        "baud_rate": 9600,
        "description": "A u-blox NEO-6M GNSS receiver breakout commonly fitted with a ceramic patch antenna, backup cell, and UART header. It receives satellite signals and emits position/time data in NMEA sentences; it requires a suitable view of the sky for a fix.",
        "working_principle": "The receiver correlates satellite ranging codes and navigation data to compute a position and time solution. Its UART streams configured NMEA sentences such as GGA and RMC. The host checks fix/status fields, parses coordinate fields, and converts NMEA degrees-and-minutes to decimal degrees.",
        "technical_specifications": {
            "Typical board size": "About 35 x 25 mm, excluding antenna cable; breakout-dependent",
            "Receiver": "u-blox NEO-6 family; up to 50 acquisition/tracking channels",
            "Update rate": "Typically up to 5 Hz for NEO-6 configurations",
            "UART": "9600 baud is a common default; configurable",
            "Supply": "Receiver IC is 3.3 V class; breakout input tolerance depends on its regulator",
            "Accuracy": "About 2.5 m CEP is a typical open-sky figure, not a guarantee",
            "Antenna": "Ceramic patch antenna; clear sky view improves reception",
        },
        "pin_configuration": [
            {"pin": "VCC", "function": "Breakout supply input; verify the board regulator and voltage range."},
            {"pin": "GND", "function": "Common ground with the host."},
            {"pin": "TXD", "function": "Module UART output; connect to the host UART RX."},
            {"pin": "RXD", "function": "Module UART input; connect to the host UART TX using compatible logic levels."},
        ],
        "inputs": ["Satellite L-band signals at the antenna", "UART configuration commands from the host"],
        "outputs": ["UART NMEA sentences (commonly GGA and RMC)", "Fix status, coordinates, time, altitude, and satellite fields when available"],
        "applications": ["Outdoor robot navigation", "Position and time logging", "Vehicle tracking", "GNSS/NMEA education"],
        "working_algorithm": [
            "Configure a UART port to the module baud rate (commonly 9600 baud, 8-N-1) and receive bytes continuously.",
            "Assemble newline-terminated NMEA sentences and verify their XOR checksum when present.",
            "Parse GGA fix quality or RMC status; reject coordinates when the fix indicator is invalid.",
            "Extract latitude and longitude in degrees-and-minutes format and convert to decimal degrees: degrees + minutes/60.",
            "Publish coordinates only with a valid fix; retain satellite count and HDOP as quality indicators rather than guarantees.",
        ],
        "example_code": "#include <TinyGPSPlus.h>\n\nTinyGPSPlus gps;\nHardwareSerial gpsSerial(1);\n\nvoid setup() {\n  Serial.begin(115200);\n  gpsSerial.begin(9600, SERIAL_8N1, 16, 17); // RX, TX\n}\n\nvoid loop() {\n  while (gpsSerial.available()) gps.encode(gpsSerial.read());\n  if (gps.location.isUpdated()) {\n    if (gps.location.isValid()) {\n      Serial.printf(\"%.6f, %.6f\\n\",\n                    gps.location.lat(), gps.location.lng());\n    } else {\n      Serial.println(\"No valid GPS fix\");\n    }\n  }\n}",
        "tags": ["sensor", "gps", "gnss", "navigation", "positioning", "satellite", "nmea", "telemetry"],
        "aliases": ["gps_module", "sensor_gps", "neo6m"],
        "library": "engineering",
        "spec_status": "example",
        "specification_note": "GPS accuracy and update rate depend on antenna, firmware configuration, sky view, interference, and breakout design.",
    },

]


def get_components():
    """Return the component catalogue used by the API."""
    return COMPONENTS


def find_component(identifier: str) -> dict | None:
    """Find a component by ID, alias, or exact tag match."""
    identifier_clean = identifier.strip().lower()
    for component in COMPONENTS:
        if component.get("id", "").lower() == identifier_clean:
            return component
        if identifier_clean in [a.lower() for a in component.get("aliases", [])]:
            return component
        if identifier_clean in [t.lower() for t in component.get("tags", [])]:
            return component
    return None
