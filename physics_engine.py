
# ==========================================
# BLUEPRINT - Robot Physics Engine
# Version: 2.0
# ==========================================
#
# UPGRADE NOTES (v1 → v2)
# ════════════════════════
# A. Added aerodynamic drag (Fd = 0.5 * rho * Cd * A * v²) in both
#    snapshot and time-based models.
# B. Separated rated torque from maximum/stall torque clearly in docstrings
#    and result keys.
# C. Added gear-ratio efficiency (gearbox_efficiency) separate from
#    drivetrain_efficiency so each can be tuned independently.
# D. Added motor power calculation (W) and motor operating status.
# E. Added wheel angular velocity (rad/s) cross-check in results.
# F. Added engineering warnings to simulate_robot() result.
# G. Added component output section: per-motor and per-wheel simulated outputs.
# H. Time-based model now uses Euler integration with constant-accel
#    fallback, allowing velocity-dependent drag to update every step.
# I. Added aerodynamic drag coefficient, frontal area, and air density
#    parameters with physically sensible defaults.
# J. Added motor overload detection.
# K. Improved negative-slope handling (downhill): robot can accelerate
#    downhill even with zero motor torque.
# L. Added slope sign support: negative slope_degrees = downhill.
# M. All SI units; every assumption documented in result["assumptions"].
#
# BACKWARD COMPATIBILITY
# ══════════════════════
# All parameters from v1 keep their names and defaults.
# All v1 output keys are preserved; new keys are additive.
# simulate_motion alias preserved.
#
import math
from typing import Optional

# ------------------------------------------
# 1. Physical constants and safety limits
# ------------------------------------------

GRAVITY: float = 9.81            # m/s²
AIR_DENSITY: float = 1.225       # kg/m³ (ISA sea-level)
MIN_MASS_KG: float = 0.01
MAX_MASS_KG: float = 100.0

MAX_MOTOR_TORQUE_NM: float = 10.0
MIN_MOTOR_COUNT: int = 1
MAX_MOTOR_COUNT: int = 20

MIN_WHEEL_RADIUS_M: float = 0.005
MAX_WHEEL_RADIUS_M: float = 0.5

MAX_SLOPE_DEGREES: float = 89.0
MAX_TRACTION_COEFFICIENT: float = 2.0
MAX_ROLLING_RESISTANCE_COEFFICIENT: float = 1.0
MAX_TRAJECTORY_SAMPLES: int = 2000

# Motor overload threshold: ratio of actual torque to rated torque
OVERLOAD_RATIO_THRESHOLD: float = 1.1


# ------------------------------------------
# 2. Numeric input validation
# ------------------------------------------

def _validate_finite_number(name: str, value: float) -> float:
    """Reject booleans, non-numbers, NaN and infinity."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number.")

    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number.")

    return float(value)


# ------------------------------------------
# 3. Motor physics helpers
# ------------------------------------------

def _linear_torque_speed(
    operating_rpm: float,
    no_load_rpm: float,
    stall_torque_nm: float,
) -> float:
    """
    Simplified linear DC motor torque-speed characteristic.

    At no-load RPM torque → 0.
    At stall (0 RPM) torque → stall_torque_nm.
    Linear interpolation between these two end-points.

    Parameters
    ----------
    operating_rpm : float
        Actual motor shaft speed (RPM).
    no_load_rpm : float
        No-load (free-running) RPM at the operating voltage.
    stall_torque_nm : float
        Stall torque at the operating voltage (Nm).

    Returns
    -------
    float
        Estimated motor torque (Nm) at the given RPM. Clipped to [0, stall_torque_nm].
    """
    if no_load_rpm <= 0.0:
        return 0.0
    speed_fraction = min(operating_rpm / no_load_rpm, 1.0)
    torque = stall_torque_nm * max(0.0, 1.0 - speed_fraction)
    return torque


def _motor_power_w(torque_nm: float, angular_velocity_rad_s: float) -> float:
    """
    Mechanical power output of a motor shaft.

    P = T × ω   (W)
    """
    return torque_nm * angular_velocity_rad_s


# ------------------------------------------
# 4. Aerodynamic drag helper
# ------------------------------------------

def _aerodynamic_drag_n(
    velocity_ms: float,
    air_density: float,
    drag_coefficient: float,
    frontal_area_m2: float,
) -> float:
    """
    Aerodynamic drag force (N).

    Fd = 0.5 × ρ × Cd × A × v²

    Returns 0.0 for zero or negative velocity (no drag when stationary).
    """
    if velocity_ms <= 0.0:
        return 0.0
    return 0.5 * air_density * drag_coefficient * frontal_area_m2 * (velocity_ms ** 2)


# ------------------------------------------
# 5. Main snapshot simulation
# ------------------------------------------

def simulate_robot(
    total_mass_kg: float,
    motor_torque_nm: float,
    motor_count: int,
    wheel_radius_m: float,
    motor_rpm: float = 100.0,
    battery_voltage_v: float = 12.0,
    slope_degrees: float = 0.0,
    traction_coefficient: float = 0.7,
    rolling_resistance_coefficient: float = 0.03,
    drivetrain_efficiency: float = 0.85,
    driven_weight_fraction: float = 1.0,
    motor_rated_voltage_v: Optional[float] = None,
    motor_no_load_rpm: Optional[float] = None,
    motor_stall_torque_nm: Optional[float] = None,
    gear_ratio: float = 1.0,
    gearbox_efficiency: float = 1.0,
    drag_coefficient: float = 0.0,
    frontal_area_m2: float = 0.1,
    operating_velocity_ms: float = 0.0,
    gravity_m_s2: float = GRAVITY,
    **kwargs,
) -> dict:
    """
    Estimate robot forces, wheel speed, acceleration, and motor operating state.

    Two calculation modes
    ─────────────────────
    Legacy mode (default):
        Uses the caller-supplied ``motor_torque_nm`` as a constant torque estimate.

    Datasheet mode (activated when all three motor spec params are provided):
        Estimates operating torque using a simplified linear DC motor
        torque-speed curve derived from no-load RPM and stall torque.

    New in v2
    ─────────
    - Aerodynamic drag (Fd = 0.5 ρ Cd A v²)
    - Gearbox efficiency separate from drivetrain efficiency
    - Motor power output (W)
    - Motor overload detection
    - Engineering warnings in result
    - Downhill slopes (negative slope_degrees)

    Important:
        All results are theoretical estimates. They are not measured values.
        Output keys are additive with v1 — no existing keys removed.

    Parameters
    ----------
    total_mass_kg : float
        Total robot mass (kg). Range: 0.01–100 kg.
    motor_torque_nm : float
        Motor rated torque (Nm). Used in legacy mode; ignored when
        datasheet mode is active. Range: 0–10 Nm.
    motor_count : int
        Number of drive motors. Range: 1–20.
    wheel_radius_m : float
        Driven wheel radius (m). Range: 0.005–0.5 m.
    motor_rpm : float
        Requested motor shaft speed (RPM). Default 100 RPM.
    battery_voltage_v : float
        Battery voltage (V). Used in datasheet mode to scale no-load RPM.
    slope_degrees : float
        Terrain slope in degrees. Positive = uphill, negative = downhill.
        Range: -89 to +89 degrees.
    traction_coefficient : float
        Coulomb friction coefficient between wheels and ground. Default 0.7.
    rolling_resistance_coefficient : float
        Rolling resistance coefficient (Crr). Default 0.03.
    drivetrain_efficiency : float
        Fraction of wheel torque delivered through the drivetrain. Default 0.85.
    driven_weight_fraction : float
        Fraction of vehicle weight on driven wheels. Default 1.0.
    motor_rated_voltage_v : float, optional
        Motor rated voltage (V). Required for datasheet mode.
    motor_no_load_rpm : float, optional
        Motor no-load RPM at rated voltage. Required for datasheet mode.
    motor_stall_torque_nm : float, optional
        Motor stall torque at rated voltage (Nm). Required for datasheet mode.
    gear_ratio : float
        Motor RPM / wheel RPM. Default 1.0 (direct drive).
    gearbox_efficiency : float
        Fraction of torque transmitted through the gearbox. Default 1.0.
    drag_coefficient : float
        Aerodynamic drag coefficient (Cd). Default 0.0 (no drag).
    frontal_area_m2 : float
        Robot frontal cross-sectional area (m²). Default 0.1 m².
    operating_velocity_ms : float
        Robot velocity used to evaluate aerodynamic drag (m/s). Default 0.

    Returns
    -------
    dict
        Forces, speeds, power, overload state, warnings, and assumptions.
    """

    # ── Validate required numeric inputs ──────────────────────────────────
    total_mass_kg              = _validate_finite_number("total_mass_kg", total_mass_kg)
    motor_torque_nm            = _validate_finite_number("motor_torque_nm", motor_torque_nm)
    wheel_radius_m             = _validate_finite_number("wheel_radius_m", wheel_radius_m)
    motor_rpm                  = _validate_finite_number("motor_rpm", motor_rpm)
    battery_voltage_v          = _validate_finite_number("battery_voltage_v", battery_voltage_v)
    slope_degrees              = _validate_finite_number("slope_degrees", slope_degrees)
    traction_coefficient       = _validate_finite_number("traction_coefficient", traction_coefficient)
    rolling_resistance_coefficient = _validate_finite_number(
        "rolling_resistance_coefficient", rolling_resistance_coefficient
    )
    drivetrain_efficiency      = _validate_finite_number("drivetrain_efficiency", drivetrain_efficiency)
    driven_weight_fraction     = _validate_finite_number("driven_weight_fraction", driven_weight_fraction)
    gear_ratio                 = _validate_finite_number("gear_ratio", gear_ratio)
    gearbox_efficiency         = _validate_finite_number("gearbox_efficiency", gearbox_efficiency)
    drag_coefficient           = _validate_finite_number("drag_coefficient", drag_coefficient)
    frontal_area_m2            = _validate_finite_number("frontal_area_m2", frontal_area_m2)
    operating_velocity_ms      = _validate_finite_number("operating_velocity_ms", operating_velocity_ms)
    gravity_m_s2               = _validate_finite_number("gravity_m_s2", gravity_m_s2)

    # Validate optional motor datasheet values
    optional_values = {
        "motor_rated_voltage_v": motor_rated_voltage_v,
        "motor_no_load_rpm":     motor_no_load_rpm,
        "motor_stall_torque_nm": motor_stall_torque_nm,
    }
    for name, value in optional_values.items():
        if value is not None:
            optional_values[name] = _validate_finite_number(name, value)

    motor_rated_voltage_v = optional_values["motor_rated_voltage_v"]
    motor_no_load_rpm     = optional_values["motor_no_load_rpm"]
    motor_stall_torque_nm = optional_values["motor_stall_torque_nm"]

    # ── Validate input ranges ──────────────────────────────────────────────
    if not MIN_MASS_KG <= total_mass_kg <= MAX_MASS_KG:
        raise ValueError(
            f"total_mass_kg must be between {MIN_MASS_KG} and {MAX_MASS_KG} kg."
        )
    if not 0 <= motor_torque_nm <= MAX_MOTOR_TORQUE_NM:
        raise ValueError(
            f"motor_torque_nm must be between 0 and {MAX_MOTOR_TORQUE_NM} Nm."
        )
    if isinstance(motor_count, bool) or not isinstance(motor_count, int):
        raise ValueError("motor_count must be an integer.")
    if not MIN_MOTOR_COUNT <= motor_count <= MAX_MOTOR_COUNT:
        raise ValueError(
            f"motor_count must be between {MIN_MOTOR_COUNT} and {MAX_MOTOR_COUNT}."
        )
    if not MIN_WHEEL_RADIUS_M <= wheel_radius_m <= MAX_WHEEL_RADIUS_M:
        raise ValueError(
            f"wheel_radius_m must be between {MIN_WHEEL_RADIUS_M} and {MAX_WHEEL_RADIUS_M} metres."
        )
    if not 0 <= motor_rpm <= 10000:
        raise ValueError("motor_rpm must be between 0 and 10000 RPM.")
    if not 1 <= battery_voltage_v <= 60:
        raise ValueError("battery_voltage_v must be between 1 and 60 V.")
    if not -MAX_SLOPE_DEGREES <= slope_degrees <= MAX_SLOPE_DEGREES:
        raise ValueError(
            f"slope_degrees must be between -{MAX_SLOPE_DEGREES} and {MAX_SLOPE_DEGREES} degrees."
        )
    if not 0 <= traction_coefficient <= MAX_TRACTION_COEFFICIENT:
        raise ValueError(
            f"traction_coefficient must be between 0 and {MAX_TRACTION_COEFFICIENT}."
        )
    if not 0 <= rolling_resistance_coefficient <= MAX_ROLLING_RESISTANCE_COEFFICIENT:
        raise ValueError(
            "rolling_resistance_coefficient must be between 0 and 1."
        )
    if not 0 < drivetrain_efficiency <= 1:
        raise ValueError(
            "drivetrain_efficiency must be greater than 0 and at most 1."
        )
    if not 0 <= driven_weight_fraction <= 1:
        raise ValueError("driven_weight_fraction must be between 0 and 1.")
    if not 1 <= gear_ratio <= 100:
        raise ValueError("gear_ratio must be between 1 and 100.")
    if not 0 < gearbox_efficiency <= 1:
        raise ValueError(
            "gearbox_efficiency must be greater than 0 and at most 1."
        )
    if drag_coefficient < 0:
        raise ValueError("drag_coefficient must be >= 0.")
    if frontal_area_m2 <= 0:
        raise ValueError("frontal_area_m2 must be > 0.")
    if operating_velocity_ms < 0:
        raise ValueError("operating_velocity_ms must be >= 0.")
    if not 0 < gravity_m_s2 <= 30:
        raise ValueError("gravity_m_s2 must be greater than 0 and at most 30 m/s².")

    # ── Datasheet mode gate ────────────────────────────────────────────────
    supplied_specs = (
        motor_rated_voltage_v is not None,
        motor_no_load_rpm     is not None,
        motor_stall_torque_nm is not None,
    )
    if any(supplied_specs) and not all(supplied_specs):
        raise ValueError(
            "Provide motor_rated_voltage_v, motor_no_load_rpm, "
            "and motor_stall_torque_nm together."
        )
    datasheet_mode = all(supplied_specs)

    if datasheet_mode:
        if not 0 < motor_rated_voltage_v <= 60:
            raise ValueError(
                "motor_rated_voltage_v must be greater than 0 and at most 60 V."
            )
        if not 0 < motor_no_load_rpm <= 10000:
            raise ValueError(
                "motor_no_load_rpm must be greater than 0 and at most 10000 RPM."
            )
        if not 0 <= motor_stall_torque_nm <= MAX_MOTOR_TORQUE_NM:
            raise ValueError(
                f"motor_stall_torque_nm must be between 0 and {MAX_MOTOR_TORQUE_NM} Nm."
            )

    # ── Motor torque and speed ─────────────────────────────────────────────
    if datasheet_mode:
        voltage_ratio         = battery_voltage_v / motor_rated_voltage_v
        effective_no_load_rpm = motor_no_load_rpm * voltage_ratio
        actual_motor_rpm      = min(motor_rpm, effective_no_load_rpm)
        estimated_motor_torque_nm = _linear_torque_speed(
            actual_motor_rpm, effective_no_load_rpm, motor_stall_torque_nm
        )
        torque_model = "linear_dc_motor_datasheet_estimate"
    else:
        actual_motor_rpm          = motor_rpm
        effective_no_load_rpm     = None
        estimated_motor_torque_nm = motor_torque_nm
        torque_model              = "user_supplied_constant_torque"

    # ── Wheel speed (kinematics) ───────────────────────────────────────────
    # Gear ratio = motor RPM / wheel RPM  →  wheel RPM = motor RPM / gear_ratio
    wheel_rpm                    = actual_motor_rpm / gear_ratio
    motor_angular_velocity_rad_s = actual_motor_rpm * (2 * math.pi / 60)
    wheel_angular_velocity_rad_s = wheel_rpm * (2 * math.pi / 60)
    wheel_speed_ms               = wheel_angular_velocity_rad_s * wheel_radius_m
    wheel_speed_kmh              = wheel_speed_ms * 3.6

    # Consistency check: v = ω × r
    _v_check = wheel_angular_velocity_rad_s * wheel_radius_m
    # (used in result for transparency; should equal wheel_speed_ms)

    # ── Wheel torque and driving force ────────────────────────────────────
    total_motor_torque_nm  = estimated_motor_torque_nm * motor_count

    # Combined efficiency: gearbox × drivetrain
    combined_efficiency    = gearbox_efficiency * drivetrain_efficiency

    # Wheel torque includes gear multiplication and efficiency losses.
    effective_wheel_torque_nm = total_motor_torque_nm * gear_ratio * combined_efficiency

    # Force at the wheel rim (torque-limited)
    torque_limited_force_n = effective_wheel_torque_nm / wheel_radius_m

    # Motor power output per motor shaft
    per_motor_power_w      = _motor_power_w(estimated_motor_torque_nm, motor_angular_velocity_rad_s)
    total_motor_power_w    = per_motor_power_w * motor_count

    # ── Traction and resistance forces ────────────────────────────────────
    angle         = math.radians(slope_degrees)
    normal_force  = total_mass_kg * gravity_m_s2 * math.cos(angle)

    traction_limit_n = traction_coefficient * normal_force * driven_weight_fraction
    driving_force_n  = min(torque_limited_force_n, traction_limit_n)

    # Gravity resistance: positive = resists uphill, negative = assists downhill
    gravity_resistance_n = total_mass_kg * gravity_m_s2 * math.sin(angle)

    # Rolling resistance always opposes motion (positive value)
    rolling_resistance_n = rolling_resistance_coefficient * normal_force

    # Aerodynamic drag at the specified operating velocity
    aero_drag_n = _aerodynamic_drag_n(
        operating_velocity_ms, AIR_DENSITY, drag_coefficient, frontal_area_m2
    )

    total_resistance_n = gravity_resistance_n + rolling_resistance_n + aero_drag_n

    # ── Net force and acceleration ────────────────────────────────────────
    net_force_n  = driving_force_n - total_resistance_n
    acceleration = net_force_n / total_mass_kg

    can_move         = net_force_n > 0
    traction_limited = traction_limit_n < torque_limited_force_n

    # ── Motor overload detection ──────────────────────────────────────────
    # Convert the modeled steady resistance back through gearing and efficiency
    # to the required torque at each motor shaft, then compare it with the
    # estimated torque available from that motor.
    required_motor_torque_nm = (
        total_resistance_n
        * wheel_radius_m
        / (
            motor_count
            * gear_ratio
            * combined_efficiency
        )
    )
    overload_detected = False
    overload_ratio = None
    if estimated_motor_torque_nm > 0:
        overload_ratio = round(
            required_motor_torque_nm / estimated_motor_torque_nm,
            4,
        )
        overload_detected = overload_ratio > OVERLOAD_RATIO_THRESHOLD
    elif required_motor_torque_nm > 0:
        overload_detected = True

    # ── Engineering warnings ──────────────────────────────────────────────
    warnings: list[str] = []

    if not can_move:
        warnings.append(
            "Net force is negative or zero: the motor cannot overcome resistance at this slope, "
            "mass, and torque. Increase torque, reduce mass, or reduce slope."
        )
    if traction_limited:
        warnings.append(
            "Driving force is limited by wheel traction, not motor torque. "
            "Increase driven weight fraction or improve wheel grip."
        )
    if overload_detected:
        if overload_ratio is not None:
            warnings.append(
                f"Motor overload detected: required torque is {overload_ratio:.2f}x the available "
                f"motor torque. Reduce load or increase motor torque."
            )
        else:
            warnings.append(
                "Motor overload detected: resistance requires torque, but the estimated "
                "motor torque is zero. Reduce load or increase motor torque."
            )
    if slope_degrees > 60:
        warnings.append(
            f"Slope of {slope_degrees:.1f}° is very steep. Results are theoretical estimates only."
        )
    if wheel_radius_m < 0.02:
        warnings.append(
            "Wheel radius < 20 mm. Small wheels reduce traction and increase "
            "rolling losses in practice."
        )
    if estimated_motor_torque_nm < 1e-6 and can_move:
        warnings.append(
            "Motor torque is effectively zero; robot is relying on initial velocity only."
        )

    # ── Build result ──────────────────────────────────────────────────────
    result = {
        # Inputs echoed back
        "total_mass_kg":   round(total_mass_kg, 3),
        "motor_count":     motor_count,
        "wheel_radius_m":  round(wheel_radius_m, 3),
        "slope_degrees":   round(slope_degrees, 3),
        "gravity_m_s2":    round(gravity_m_s2, 4),

        # Motor model
        "motor_torque_model":        torque_model,
        "estimated_motor_torque_nm": round(estimated_motor_torque_nm, 4),
        "total_motor_torque_nm":     round(total_motor_torque_nm, 4),

        # Wheel torque (v2 adds separate gearbox efficiency)
        "effective_wheel_torque_nm": round(effective_wheel_torque_nm, 4),
        "effective_torque_nm":       round(effective_wheel_torque_nm, 4),  # v1 compat alias
        "gearbox_efficiency":        round(gearbox_efficiency, 4),
        "combined_efficiency":       round(combined_efficiency, 4),

        # Speeds
        "motor_rpm":                      round(actual_motor_rpm, 3),
        "battery_voltage_v":              round(battery_voltage_v, 3),
        "gear_ratio":                     round(gear_ratio, 3),
        "wheel_rpm":                      round(wheel_rpm, 3),
        "motor_angular_velocity_rad_s":   round(motor_angular_velocity_rad_s, 3),
        "wheel_angular_velocity_rad_s":   round(wheel_angular_velocity_rad_s, 3),
        "theoretical_wheel_speed_ms":     round(wheel_speed_ms, 3),
        "theoretical_wheel_speed_kmh":    round(wheel_speed_kmh, 3),

        # Motor power (new in v2)
        "per_motor_power_w":   round(per_motor_power_w, 3),
        "total_motor_power_w": round(total_motor_power_w, 3),

        # Forces
        "torque_limited_force_n":  round(torque_limited_force_n, 3),
        "traction_limit_n":        round(traction_limit_n, 3),
        "driving_force_n":         round(driving_force_n, 3),
        "gravity_resistance_n":    round(gravity_resistance_n, 3),
        "rolling_resistance_n":    round(rolling_resistance_n, 3),
        "aero_drag_n":             round(aero_drag_n, 3),
        "total_resistance_n":      round(total_resistance_n, 3),
        "normal_force_n":          round(normal_force, 3),
        "net_force_n":             round(net_force_n, 3),
        "theoretical_acceleration_ms2": round(acceleration, 3),

        # Motion capability
        "can_move_under_model": can_move,
        "traction_limited":     traction_limited,

        # Motor overload (new in v2)
        "motor_overload_detected": overload_detected,
        "motor_overload_ratio":    overload_ratio,

        # Engineering warnings (new in v2)
        "engineering_warnings": warnings,

        "assumptions": [
            "Constant mass and slope during the simulation",
            "Simplified linear DC motor torque-speed curve (datasheet mode only)",
            "Simplified Coulomb traction limit on driven wheels",
            "Constant rolling resistance coefficient (Crr)",
            "Uniform gravitational acceleration supplied for the test environment",
            "Driven weight fraction is an estimate; axle load transfer not modelled",
            "Aerodynamic drag evaluated at the supplied operating_velocity_ms",
            "Gear ratio is motor RPM divided by wheel RPM",
            "Gearbox efficiency is separate from drivetrain efficiency",
            "No motor current, thermal, or electrical model",
            "No wheel-slip dynamics beyond the Coulomb traction limit",
            "Wheel speed assumes pure rolling (zero wheel slip)",
            (
                "Datasheet mode: linear torque-speed curve, voltage-scaled no-load RPM"
                if datasheet_mode
                else "Legacy mode: constant user-supplied motor torque"
            ),
        ],
    }

    # Datasheet-specific fields
    if datasheet_mode:
        result.update({
            "motor_rated_voltage_v":  round(motor_rated_voltage_v, 3),
            "motor_no_load_rpm":      round(motor_no_load_rpm, 3),
            "effective_no_load_rpm":  round(effective_no_load_rpm, 3),
            "motor_stall_torque_nm":  round(motor_stall_torque_nm, 4),
        })

    return result


# ------------------------------------------
# 6. Time-based robot motion simulation
# ------------------------------------------

def simulate_robot_motion(
    total_mass_kg: float,
    motor_torque_nm: float,
    motor_count: int,
    wheel_radius_m: float,
    duration_s: float = 5.0,
    time_step_s: float = 0.1,
    initial_velocity_ms: float = 0.0,
    initial_position_m: float = 0.0,
    motor_rpm: float = 100.0,
    battery_voltage_v: float = 12.0,
    slope_degrees: float = 0.0,
    traction_coefficient: float = 0.7,
    rolling_resistance_coefficient: float = 0.03,
    drivetrain_efficiency: float = 0.85,
    driven_weight_fraction: float = 1.0,
    motor_rated_voltage_v: Optional[float] = None,
    motor_no_load_rpm: Optional[float] = None,
    motor_stall_torque_nm: Optional[float] = None,
    gear_ratio: float = 1.0,
    gearbox_efficiency: float = 1.0,
    drag_coefficient: float = 0.0,
    frontal_area_m2: float = 0.1,
    gravity_m_s2: float = GRAVITY,
    **kwargs,
) -> dict:
    """
    Simulate time-based robot motion using Euler integration.

    Integrates position and velocity over ``duration_s`` using steps of
    ``time_step_s``. Aerodynamic drag is recalculated each step based on the
    current velocity, so the drag force updates continuously.

    Motion Regimes
    ──────────────
    Driving phase:
        Net driving force exceeds resistance → robot accelerates.
    Cruising phase:
        Velocity reaches the top speed implied by wheel RPM → motor force
        is clamped to exactly cancel resistance; acceleration = 0.
    Deceleration / stopping:
        Net force is negative → robot decelerates; stops at v = 0 (no reverse).
    Overspeed coast-down:
        Initial velocity exceeds top speed → motor is modelled as disengaged
        (freewheeling); only drag and resistance act until v ≤ top_speed.

    New in v2
    ─────────
    - Aerodynamic drag recalculated every time step (velocity-dependent).
    - Negative slope (downhill) supported: gravity can accelerate the robot.
    - Euler integration replaces piecewise-analytical model for generality.
    - Component outputs section added (motor, wheel per-step state at t=end).

    Backward Compatibility
    ──────────────────────
    All v1 output keys present. New keys are additive only.
    ``simulate_motion`` alias preserved at module level.
    """

    # ── Validate time and motion inputs ───────────────────────────────────
    duration_s            = _validate_finite_number("duration_s", duration_s)
    time_step_s           = _validate_finite_number("time_step_s", time_step_s)
    initial_velocity_ms   = _validate_finite_number("initial_velocity_ms", initial_velocity_ms)
    initial_position_m    = _validate_finite_number("initial_position_m", initial_position_m)

    if not 0.0 <= duration_s <= 3600.0:
        raise ValueError("duration_s must be between 0 and 3600 seconds.")
    if not 0.001 <= time_step_s <= 10.0:
        raise ValueError("time_step_s must be between 0.001 and 10.0 seconds.")
    if initial_velocity_ms < 0.0:
        raise ValueError("initial_velocity_ms must be non-negative.")
    if initial_position_m < 0.0:
        raise ValueError("initial_position_m must be non-negative.")

    # Trajectory sample cap
    if time_step_s > 0 and duration_s > 0:
        estimated_samples = int(math.ceil(duration_s / time_step_s)) + 1
        if estimated_samples > MAX_TRAJECTORY_SAMPLES:
            raise ValueError(
                f"The combination of duration_s={duration_s} and time_step_s={time_step_s} "
                f"would generate {estimated_samples} trajectory samples, exceeding the "
                f"safety limit of {MAX_TRAJECTORY_SAMPLES}. Increase time_step_s or reduce duration_s."
            )

    # ── Run the base snapshot for validated forces ─────────────────────────
    # Evaluate forces at zero velocity first; drag will be re-evaluated per step.
    base_sim = simulate_robot(
        total_mass_kg=total_mass_kg,
        motor_torque_nm=motor_torque_nm,
        motor_count=motor_count,
        wheel_radius_m=wheel_radius_m,
        motor_rpm=motor_rpm,
        battery_voltage_v=battery_voltage_v,
        slope_degrees=slope_degrees,
        traction_coefficient=traction_coefficient,
        rolling_resistance_coefficient=rolling_resistance_coefficient,
        drivetrain_efficiency=drivetrain_efficiency,
        driven_weight_fraction=driven_weight_fraction,
        motor_rated_voltage_v=motor_rated_voltage_v,
        motor_no_load_rpm=motor_no_load_rpm,
        motor_stall_torque_nm=motor_stall_torque_nm,
        gear_ratio=gear_ratio,
        gearbox_efficiency=gearbox_efficiency,
        drag_coefficient=drag_coefficient,
        frontal_area_m2=frontal_area_m2,
        gravity_m_s2=gravity_m_s2,
        operating_velocity_ms=0.0,   # drag evaluated per step in Euler loop
    )

    top_speed_ms          = base_sim["theoretical_wheel_speed_ms"]
    driving_force_n       = base_sim["driving_force_n"]
    gravity_resistance_n  = base_sim["gravity_resistance_n"]
    rolling_resistance_n  = base_sim["rolling_resistance_n"]
    wheel_circumference_m = 2.0 * math.pi * wheel_radius_m

    # ── Build sample time grid ─────────────────────────────────────────────
    if duration_s == 0.0:
        sample_times = [0.0]
    else:
        sample_times = []
        current_t    = 0.0
        epsilon      = 1e-9
        while current_t < duration_s - epsilon:
            sample_times.append(current_t)
            current_t += time_step_s
        # Guarantee the final sample is exactly at duration_s
        if not sample_times or sample_times[-1] < duration_s - epsilon:
            sample_times.append(duration_s)
        else:
            sample_times[-1] = duration_s

    # ── Euler integration ─────────────────────────────────────────────────
    trajectory: list[dict] = []
    pos = initial_position_m
    vel = initial_velocity_ms
    t   = 0.0

    for i, t_target in enumerate(sample_times):
        # Integrate from previous time to t_target
        if i > 0:
            dt = t_target - sample_times[i - 1]
            if dt > 0:
                # Choose the driving regime at the current velocity
                if vel > top_speed_ms:
                    # Overspeed coast-down: motor disengaged
                    drag_at_v = _aerodynamic_drag_n(vel, AIR_DENSITY, drag_coefficient, frontal_area_m2)
                    # Downhill: gravity_resistance_n can be negative (assists)
                    resistance = rolling_resistance_n + gravity_resistance_n + drag_at_v
                    # Only resistance acts; no driving force
                    acc = -resistance / total_mass_kg
                elif vel < top_speed_ms and driving_force_n > (rolling_resistance_n + gravity_resistance_n):
                    # Driving phase: motor actively accelerates
                    drag_at_v  = _aerodynamic_drag_n(vel, AIR_DENSITY, drag_coefficient, frontal_area_m2)
                    resistance = rolling_resistance_n + gravity_resistance_n + drag_at_v
                    net        = driving_force_n - resistance
                    acc        = net / total_mass_kg
                else:
                    # Cruising or stall: net force clipped to match resistance
                    drag_at_v  = _aerodynamic_drag_n(vel, AIR_DENSITY, drag_coefficient, frontal_area_m2)
                    resistance = rolling_resistance_n + gravity_resistance_n + drag_at_v
                    net        = driving_force_n - resistance
                    if net < 0.0 and vel <= 0.0:
                        acc = 0.0   # already stopped
                    else:
                        acc = net / total_mass_kg

                new_vel = vel + acc * dt

                # Clamp to top speed if overshooting
                if vel <= top_speed_ms and new_vel > top_speed_ms:
                    # Time to reach top speed within this step (analytical)
                    if abs(acc) > 1e-9:
                        t_top  = (top_speed_ms - vel) / acc
                        pos   += vel * t_top + 0.5 * acc * t_top ** 2
                        pos   += top_speed_ms * (dt - t_top)
                    else:
                        pos += vel * dt
                    new_vel = top_speed_ms
                else:
                    pos += vel * dt + 0.5 * acc * dt ** 2

                # Prevent negative velocity (no backward rolling)
                vel = max(0.0, new_vel)
                # Once stopped on a hill with no driving force, hold at 0
                if vel == 0.0 and driving_force_n <= (rolling_resistance_n + gravity_resistance_n):
                    vel = 0.0

        # Sample at this time
        t            = t_target
        displacement = pos - initial_position_m
        rotations    = displacement / wheel_circumference_m if wheel_circumference_m > 0 else 0.0
        w_rpm        = (vel / wheel_radius_m) * (60.0 / (2.0 * math.pi)) if wheel_radius_m > 0 else 0.0

        # Recompute current acceleration for the sample record
        if vel > top_speed_ms:
            drag_at_v = _aerodynamic_drag_n(vel, AIR_DENSITY, drag_coefficient, frontal_area_m2)
            cur_acc = -(rolling_resistance_n + gravity_resistance_n + drag_at_v) / total_mass_kg
        elif driving_force_n > (rolling_resistance_n + gravity_resistance_n):
            drag_at_v = _aerodynamic_drag_n(vel, AIR_DENSITY, drag_coefficient, frontal_area_m2)
            cur_acc = (driving_force_n - rolling_resistance_n - gravity_resistance_n - drag_at_v) / total_mass_kg
        else:
            cur_acc = 0.0

        if vel == 0.0:
            cur_acc = 0.0   # stationary: no acceleration displayed

        trajectory.append({
            "time_s":            round(t, 3),
            "position_m":        round(pos, 3),
            "velocity_ms":       round(vel, 3),
            "acceleration_ms2":  round(cur_acc, 3),
            "wheel_rotations":   round(rotations, 3),
            "wheel_rpm":         round(w_rpm, 3),
        })

    # ── Summary ───────────────────────────────────────────────────────────
    final = trajectory[-1]
    final_pos = final["position_m"]
    final_vel = final["velocity_ms"]
    final_acc = final["acceleration_ms2"]

    total_distance_m  = final_pos - initial_position_m
    total_rotations   = total_distance_m / wheel_circumference_m if wheel_circumference_m > 0 else 0.0
    final_wheel_rpm   = (final_vel / wheel_radius_m) * (60.0 / (2.0 * math.pi)) if wheel_radius_m > 0 else 0.0

    # Top speed reached detection
    if initial_velocity_ms >= top_speed_ms:
        top_speed_reached   = any(abs(p["velocity_ms"] - top_speed_ms) < 0.01 for p in trajectory)
        time_to_top_speed_s = next(
            (p["time_s"] for p in trajectory if abs(p["velocity_ms"] - top_speed_ms) < 0.01),
            None
        )
    else:
        reached_pts = [p for p in trajectory if p["velocity_ms"] >= top_speed_ms - 0.001]
        if reached_pts:
            top_speed_reached   = True
            time_to_top_speed_s = round(reached_pts[0]["time_s"], 3)
        else:
            top_speed_reached   = False
            time_to_top_speed_s = None

    # ── Component outputs (new in v2) ─────────────────────────────────────
    # Simulated operating state at the end of the simulation.
    # These are model estimates, NOT measured sensor readings.
    final_motor_omega  = base_sim["motor_angular_velocity_rad_s"]
    final_per_motor_torque = base_sim["estimated_motor_torque_nm"]
    final_motor_power  = _motor_power_w(final_per_motor_torque, final_motor_omega)

    motor_outputs = {
        "simulated_motor_operating_torque_nm": round(final_per_motor_torque, 4),
        "simulated_motor_rpm":                 round(base_sim["motor_rpm"], 3),
        "simulated_motor_power_w":             round(final_motor_power, 3),
        "simulated_total_motor_power_w":       round(final_motor_power * motor_count, 3),
        "motor_overload":                      base_sim["motor_overload_detected"],
        "note":                                "Simulated motor state — not a measured sensor reading.",
    }
    wheel_outputs = {
        "simulated_final_wheel_rpm":           round(final_wheel_rpm, 3),
        "simulated_final_wheel_omega_rad_s":   round(
            final_vel / wheel_radius_m if wheel_radius_m > 0 else 0.0, 3
        ),
        "simulated_final_linear_speed_ms":     round(final_vel, 3),
        "simulated_total_wheel_rotations":     round(total_rotations, 3),
        "note":                                "Simulated wheel state — not a measured sensor reading.",
    }

    res = {
        "duration_s":              round(duration_s, 3),
        "time_step_s":             round(time_step_s, 3),
        "initial_velocity_ms":     round(initial_velocity_ms, 3),
        "initial_position_m":      round(initial_position_m, 3),
        "final_position_m":        round(final_pos, 3),
        "distance_traveled_m":     round(total_distance_m, 3),
        "final_velocity_ms":       round(final_vel, 3),
        "final_velocity_kmh":      round(final_vel * 3.6, 3),
        "final_acceleration_ms2":  round(final_acc, 3),
        "top_speed_reached":       top_speed_reached,
        "time_to_top_speed_s":     time_to_top_speed_s,
        "wheel_radius_m":          round(wheel_radius_m, 3),
        "wheel_rotations":         round(total_rotations, 3),
        "wheel_rotation_deg":      round(total_rotations * 360.0, 2),
        "wheel_rotation_rad":      round(
            total_distance_m / wheel_radius_m if wheel_radius_m > 0 else 0.0, 3
        ),
        "final_wheel_rpm":         round(final_wheel_rpm, 3),
        "net_force_n":             round(base_sim["net_force_n"], 3),
        "driving_force_n":         round(driving_force_n, 3),
        "traction_limit_n":        round(base_sim["traction_limit_n"], 3),
        "traction_limited":        base_sim["traction_limited"],
        "gravity_resistance_n":    round(gravity_resistance_n, 3),
        "slope_resistance_n":      round(gravity_resistance_n, 3),   # v1 alias
        "rolling_resistance_n":    round(rolling_resistance_n, 3),
        "aero_drag_n":             round(base_sim["aero_drag_n"], 3),
        "can_move":                base_sim["can_move_under_model"],
        "motion_model":            "euler_integration_v2",
        "engineering_warnings":    base_sim["engineering_warnings"],
        "motor_outputs":           motor_outputs,
        "wheel_outputs":           wheel_outputs,
        "trajectory":              trajectory,
        "base_simulation":         base_sim,
        "assumptions": [
            "Euler integration with velocity-dependent aerodynamic drag",
            "Driving force limited by motor torque-gearing or Coulomb traction limit",
            "Top speed bounded by no-load / operating wheel angular velocity",
            "Motor modelled as disengaged (freewheeling) during overspeed coast-down",
            "Robot stops at zero velocity; no backward roll-back modelled",
            "Pure rolling contact assumed (zero wheel slip beyond Coulomb limit)",
            "Trajectory samples capped at MAX_TRAJECTORY_SAMPLES to prevent memory exhaustion",
            "Aerodynamic drag recalculated every time step from current velocity",
            "Negative slope_degrees = downhill (gravity assists motion)",
            "Uniform gravitational acceleration supplied for the test environment",
            "Component outputs are simulated estimates, not measured sensor readings",
        ],
    }

    return res


# Retain v1 alias for flexibility
simulate_motion = simulate_robot_motion
