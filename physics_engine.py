
# ==========================================
# BLUEPRINT - Robot Physics Engine
# ==========================================

import math

# ------------------------------------------
# 1. Physical constants and safety limits
# ------------------------------------------

GRAVITY = 9.81

MIN_MASS_KG = 0.01
MAX_MASS_KG = 100.0

MAX_MOTOR_TORQUE_NM = 10.0
MIN_MOTOR_COUNT = 1
MAX_MOTOR_COUNT = 20

MIN_WHEEL_RADIUS_M = 0.005
MAX_WHEEL_RADIUS_M = 0.5

MAX_SLOPE_DEGREES = 89.0
MAX_TRACTION_COEFFICIENT = 2.0
MAX_ROLLING_RESISTANCE_COEFFICIENT = 1.0
MAX_TRAJECTORY_SAMPLES = 2000


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
# 3. Robot simulation
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
    motor_rated_voltage_v: float | None = None,
    motor_no_load_rpm: float | None = None,
    motor_stall_torque_nm: float | None = None,
    gear_ratio: float = 1.0,
) -> dict:
    """
    Estimate robot forces, wheel speed and acceleration.

    Legacy mode:
        Uses the supplied motor_torque_nm.

    Datasheet mode:
        Estimates torque using a simplified linear DC motor curve.

    Important:
        These are theoretical estimates, not measured performance.
    """

    # --------------------------------------
    # 4. Validate required numeric inputs
    # --------------------------------------

    total_mass_kg = _validate_finite_number(
        "total_mass_kg", total_mass_kg
    )
    motor_torque_nm = _validate_finite_number(
        "motor_torque_nm", motor_torque_nm
    )
    wheel_radius_m = _validate_finite_number(
        "wheel_radius_m", wheel_radius_m
    )
    motor_rpm = _validate_finite_number("motor_rpm", motor_rpm)
    battery_voltage_v = _validate_finite_number(
        "battery_voltage_v", battery_voltage_v
    )
    slope_degrees = _validate_finite_number(
        "slope_degrees", slope_degrees
    )
    traction_coefficient = _validate_finite_number(
        "traction_coefficient", traction_coefficient
    )
    rolling_resistance_coefficient = _validate_finite_number(
        "rolling_resistance_coefficient",
        rolling_resistance_coefficient,
    )
    drivetrain_efficiency = _validate_finite_number(
        "drivetrain_efficiency", drivetrain_efficiency
    )
    driven_weight_fraction = _validate_finite_number(
        "driven_weight_fraction", driven_weight_fraction
    )
    gear_ratio = _validate_finite_number("gear_ratio", gear_ratio)

    # Validate optional motor datasheet values.
    optional_values = {
        "motor_rated_voltage_v": motor_rated_voltage_v,
        "motor_no_load_rpm": motor_no_load_rpm,
        "motor_stall_torque_nm": motor_stall_torque_nm,
    }

    for name, value in optional_values.items():
        if value is not None:
            optional_values[name] = _validate_finite_number(
                name, value
            )

    motor_rated_voltage_v = optional_values["motor_rated_voltage_v"]
    motor_no_load_rpm = optional_values["motor_no_load_rpm"]
    motor_stall_torque_nm = optional_values["motor_stall_torque_nm"]

    # --------------------------------------
    # 5. Validate input ranges
    # --------------------------------------

    if not MIN_MASS_KG <= total_mass_kg <= MAX_MASS_KG:
        raise ValueError(
            f"total_mass_kg must be between {MIN_MASS_KG} "
            f"and {MAX_MASS_KG} kg."
        )

    if not 0 <= motor_torque_nm <= MAX_MOTOR_TORQUE_NM:
        raise ValueError(
            f"motor_torque_nm must be between 0 and "
            f"{MAX_MOTOR_TORQUE_NM} Nm."
        )

    if isinstance(motor_count, bool) or not isinstance(motor_count, int):
        raise ValueError("motor_count must be an integer.")

    if not MIN_MOTOR_COUNT <= motor_count <= MAX_MOTOR_COUNT:
        raise ValueError(
            f"motor_count must be between {MIN_MOTOR_COUNT} "
            f"and {MAX_MOTOR_COUNT}."
        )

    if not MIN_WHEEL_RADIUS_M <= wheel_radius_m <= MAX_WHEEL_RADIUS_M:
        raise ValueError(
            f"wheel_radius_m must be between {MIN_WHEEL_RADIUS_M} "
            f"and {MAX_WHEEL_RADIUS_M} metres."
        )

    if not 0 <= motor_rpm <= 10000:
        raise ValueError("motor_rpm must be between 0 and 10000 RPM.")

    if not 1 <= battery_voltage_v <= 60:
        raise ValueError("battery_voltage_v must be between 1 and 60 V.")

    if not 0 <= slope_degrees <= MAX_SLOPE_DEGREES:
        raise ValueError(
            f"slope_degrees must be between 0 and "
            f"{MAX_SLOPE_DEGREES} degrees."
        )

    if not 0 <= traction_coefficient <= MAX_TRACTION_COEFFICIENT:
        raise ValueError(
            f"traction_coefficient must be between 0 and "
            f"{MAX_TRACTION_COEFFICIENT}."
        )

    if not 0 <= rolling_resistance_coefficient <= (
        MAX_ROLLING_RESISTANCE_COEFFICIENT
    ):
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

    # --------------------------------------
    # 6. Select the motor calculation mode
    # --------------------------------------

    supplied_specs = (
        motor_rated_voltage_v is not None,
        motor_no_load_rpm is not None,
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
                "motor_rated_voltage_v must be greater than 0 "
                "and at most 60 V."
            )

        if not 0 < motor_no_load_rpm <= 10000:
            raise ValueError(
                "motor_no_load_rpm must be greater than 0 "
                "and at most 10000 RPM."
            )

        if not 0 <= motor_stall_torque_nm <= MAX_MOTOR_TORQUE_NM:
            raise ValueError(
                f"motor_stall_torque_nm must be between 0 and "
                f"{MAX_MOTOR_TORQUE_NM} Nm."
            )

    # --------------------------------------
    # 7. Estimate motor torque and speed
    # --------------------------------------

    if datasheet_mode:
        # Approximation: no-load RPM scales linearly with voltage.
        voltage_ratio = battery_voltage_v / motor_rated_voltage_v
        effective_no_load_rpm = motor_no_load_rpm * voltage_ratio

        # Cap requested speed at the estimated no-load RPM.
        actual_motor_rpm = min(motor_rpm, effective_no_load_rpm)

        # Simplified linear torque-speed curve.
        speed_fraction = actual_motor_rpm / effective_no_load_rpm

        estimated_motor_torque_nm = (
            motor_stall_torque_nm
            * max(0.0, 1.0 - speed_fraction)
        )

        torque_model = "linear_dc_motor_datasheet_estimate"

    else:
        # Backward-compatible mode.
        actual_motor_rpm = motor_rpm
        effective_no_load_rpm = None
        estimated_motor_torque_nm = motor_torque_nm

        torque_model = "user_supplied_constant_torque"

    # --------------------------------------
    # 8. Calculate wheel speed
    # --------------------------------------

    # Gear ratio = motor RPM / wheel RPM.
    wheel_rpm = actual_motor_rpm / gear_ratio

    motor_angular_velocity_rad_s = actual_motor_rpm * (
        2 * math.pi / 60
    )
    wheel_angular_velocity_rad_s = wheel_rpm * (
        2 * math.pi / 60
    )

    wheel_speed_ms = wheel_angular_velocity_rad_s * wheel_radius_m
    wheel_speed_kmh = wheel_speed_ms * 3.6

    # --------------------------------------
    # 9. Calculate wheel torque and forces
    # --------------------------------------

    total_motor_torque = estimated_motor_torque_nm * motor_count

    # Wheel torque includes gearing and drivetrain losses.
    effective_wheel_torque = (
        total_motor_torque * gear_ratio * drivetrain_efficiency
    )

    torque_limited_force = effective_wheel_torque / wheel_radius_m

    # --------------------------------------
    # 10. Calculate traction and resistance
    # --------------------------------------

    angle = math.radians(slope_degrees)

    normal_force = (
        total_mass_kg * GRAVITY * math.cos(angle)
    )

    traction_limit = (
        traction_coefficient
        * normal_force
        * driven_weight_fraction
    )

    driving_force = min(torque_limited_force, traction_limit)

    gravity_resistance = (
        total_mass_kg * GRAVITY * math.sin(angle)
    )

    rolling_resistance = (
        rolling_resistance_coefficient * normal_force
    )

    # --------------------------------------
    # 11. Calculate net force and acceleration
    # --------------------------------------

    net_force = (
        driving_force
        - gravity_resistance
        - rolling_resistance
    )

    acceleration = net_force / total_mass_kg

    can_move = net_force > 0
    traction_limited = traction_limit < torque_limited_force

    # --------------------------------------
    # 12. Build results
    # --------------------------------------

    result = {
        "total_mass_kg": round(total_mass_kg, 3),
        "motor_count": motor_count,
        "wheel_radius_m": round(wheel_radius_m, 3),
        "slope_degrees": round(slope_degrees, 3),

        "motor_torque_model": torque_model,
        "estimated_motor_torque_nm": round(
            estimated_motor_torque_nm, 4
        ),
        "total_motor_torque_nm": round(total_motor_torque, 4),

        # Clear name for the torque available at the wheels.
        "effective_wheel_torque_nm": round(
            effective_wheel_torque, 4
        ),

        # Retain the old field for frontend and test compatibility.
        "effective_torque_nm": round(effective_wheel_torque, 4),

        "motor_rpm": round(actual_motor_rpm, 3),
        "battery_voltage_v": round(battery_voltage_v, 3),
        "gear_ratio": round(gear_ratio, 3),
        "wheel_rpm": round(wheel_rpm, 3),

        "motor_angular_velocity_rad_s": round(
            motor_angular_velocity_rad_s, 3
        ),
        "wheel_angular_velocity_rad_s": round(
            wheel_angular_velocity_rad_s, 3
        ),
        "theoretical_wheel_speed_ms": round(wheel_speed_ms, 3),
        "theoretical_wheel_speed_kmh": round(wheel_speed_kmh, 3),

        "torque_limited_force_n": round(torque_limited_force, 3),
        "traction_limit_n": round(traction_limit, 3),
        "driving_force_n": round(driving_force, 3),
        "gravity_resistance_n": round(gravity_resistance, 3),
        "rolling_resistance_n": round(rolling_resistance, 3),
        "normal_force_n": round(normal_force, 3),
        "net_force_n": round(net_force, 3),
        "theoretical_acceleration_ms2": round(acceleration, 3),

        "can_move_under_model": can_move,
        "traction_limited": traction_limited,

        "assumptions": [
            "Constant mass and slope during the simulation",
            "Simplified Coulomb traction limit",
            "Constant rolling resistance coefficient",
            "Driven weight fraction is an estimate",
            "No aerodynamic drag or battery voltage sag",
            "No motor current or thermal limit",
            "No detailed motor-controller electrical model",
            "No wheel-slip dynamics",
            "Wheel speed assumes no wheel slip",
            "Gear ratio is motor RPM divided by wheel RPM",
            (
                "Datasheet mode uses a linear torque-speed curve "
                "and voltage-scaled no-load RPM"
                if datasheet_mode
                else "Legacy mode assumes constant user-supplied motor torque"
            ),
        ],
    }

    # Include datasheet information only when that mode is active.
    if datasheet_mode:
        result.update({
            "motor_rated_voltage_v": round(
                motor_rated_voltage_v, 3
            ),
            "motor_no_load_rpm": round(
                motor_no_load_rpm, 3
            ),
            "effective_no_load_rpm": round(
                effective_no_load_rpm, 3
            ),
            "motor_stall_torque_nm": round(
                motor_stall_torque_nm, 4
            ),
        })

    return result


# ------------------------------------------
# 4. Time-based robot motion simulation
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
    motor_rated_voltage_v: float | None = None,
    motor_no_load_rpm: float | None = None,
    motor_stall_torque_nm: float | None = None,
    gear_ratio: float = 1.0,
) -> dict:
    """
    Simulate time-based robot motion across position, velocity, acceleration,
    slope resistance, and wheel rotation.

    Motion Model:
        Piecewise constant-acceleration model. Forces and traction limits are
        derived from simulate_robot(). Kinematics are integrated analytically:
          - Acceleration phase: accelerates under net driving force until top speed.
          - Cruising phase: maintains top speed when motor force balances resistances.
          - Deceleration phase: slows down under negative net force until stopping.
          - Overspeed coast-down: if initial velocity exceeds top speed, the motor
            is assumed disengaged (freewheeling), and coast-down deceleration occurs
            under opposing resistance (gravity + rolling) until reaching top speed
            or stopping.
    """

    # 1. Validate time and motion inputs
    duration_s = _validate_finite_number("duration_s", duration_s)
    time_step_s = _validate_finite_number("time_step_s", time_step_s)
    initial_velocity_ms = _validate_finite_number(
        "initial_velocity_ms", initial_velocity_ms
    )
    initial_position_m = _validate_finite_number(
        "initial_position_m", initial_position_m
    )

    if not 0.0 <= duration_s <= 3600.0:
        raise ValueError("duration_s must be between 0 and 3600 seconds.")

    if not 0.001 <= time_step_s <= 10.0:
        raise ValueError("time_step_s must be between 0.001 and 10.0 seconds.")

    if initial_velocity_ms < 0.0:
        raise ValueError("initial_velocity_ms must be non-negative.")

    if initial_position_m < 0.0:
        raise ValueError("initial_position_m must be non-negative.")

    # Prevent excessive trajectory samples from consuming unreasonable memory
    if time_step_s > 0:
        estimated_samples = int(math.ceil(duration_s / time_step_s)) + 1
        if estimated_samples > MAX_TRAJECTORY_SAMPLES:
            raise ValueError(
                f"The combination of duration_s={duration_s} and time_step_s={time_step_s} "
                f"would generate {estimated_samples} trajectory samples, exceeding the "
                f"safety limit of {MAX_TRAJECTORY_SAMPLES}. Increase time_step_s or reduce duration_s."
            )

    # 2. Leverage simulate_robot() for physical validation and force calculation
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
    )

    top_speed_ms = base_sim["theoretical_wheel_speed_ms"]
    driving_force_n = base_sim["driving_force_n"]
    gravity_resistance_n = base_sim["gravity_resistance_n"]
    rolling_resistance_n = base_sim["rolling_resistance_n"]
    total_resistance_n = gravity_resistance_n + rolling_resistance_n
    net_force_n = base_sim["net_force_n"]
    wheel_circumference_m = 2.0 * math.pi * wheel_radius_m

    # Opposing resistance deceleration when motor is freewheeling/disengaged
    opposing_accel_ms2 = -total_resistance_n / total_mass_kg
    # Net acceleration when motor is actively driving
    driving_accel_ms2 = net_force_n / total_mass_kg

    # 3. Kinematic state solver
    def get_motion_state(t: float) -> tuple[float, float, float]:
        """
        Calculates exact (position_m, velocity_ms, acceleration_ms2) at time t >= 0.
        Analytical solution guarantees zero drift, smooth coast-down, and no reverse rollback.
        """
        if t <= 0.0:
            if initial_velocity_ms > top_speed_ms:
                init_a = opposing_accel_ms2
            elif initial_velocity_ms < top_speed_ms and net_force_n > 0.0:
                init_a = driving_accel_ms2
            elif initial_velocity_ms > 0.0 and net_force_n < 0.0:
                init_a = driving_accel_ms2
            else:
                init_a = 0.0
            return initial_position_m, initial_velocity_ms, init_a

        # Case A: Overspeed coast-down (motor disengaged/freewheeling)
        if initial_velocity_ms > top_speed_ms:
            if opposing_accel_ms2 < 0.0:
                t_to_top = (top_speed_ms - initial_velocity_ms) / opposing_accel_ms2
            else:
                t_to_top = float("inf")

            if t <= t_to_top:
                v = initial_velocity_ms + opposing_accel_ms2 * t
                x = initial_position_m + initial_velocity_ms * t + 0.5 * opposing_accel_ms2 * (t ** 2)
                return x, max(0.0, v), opposing_accel_ms2
            else:
                x_at_top = (
                    initial_position_m
                    + initial_velocity_ms * t_to_top
                    + 0.5 * opposing_accel_ms2 * (t_to_top ** 2)
                )
                t_after_top = t - t_to_top

                # Motor re-engages at top speed
                if net_force_n >= 0.0:
                    x = x_at_top + top_speed_ms * t_after_top
                    return x, top_speed_ms, 0.0
                else:
                    t_to_stop = -top_speed_ms / driving_accel_ms2
                    if t_after_top <= t_to_stop:
                        v = top_speed_ms + driving_accel_ms2 * t_after_top
                        x = (
                            x_at_top
                            + top_speed_ms * t_after_top
                            + 0.5 * driving_accel_ms2 * (t_after_top ** 2)
                        )
                        return x, max(0.0, v), driving_accel_ms2
                    else:
                        x_stop = (
                            x_at_top
                            + top_speed_ms * t_to_stop
                            + 0.5 * driving_accel_ms2 * (t_to_stop ** 2)
                        )
                        return x_stop, 0.0, 0.0

        # Case B: Initial velocity is at or below top speed
        if net_force_n > 0.0:
            t_to_top = (
                (top_speed_ms - initial_velocity_ms) / driving_accel_ms2
                if driving_accel_ms2 > 0.0
                else float("inf")
            )

            if t <= t_to_top:
                v = initial_velocity_ms + driving_accel_ms2 * t
                x = initial_position_m + initial_velocity_ms * t + 0.5 * driving_accel_ms2 * (t ** 2)
                return x, min(v, top_speed_ms), driving_accel_ms2
            else:
                x_at_top = (
                    initial_position_m
                    + initial_velocity_ms * t_to_top
                    + 0.5 * driving_accel_ms2 * (t_to_top ** 2)
                )
                x = x_at_top + top_speed_ms * (t - t_to_top)
                return x, top_speed_ms, 0.0

        elif net_force_n < 0.0:
            if initial_velocity_ms <= 0.0:
                return initial_position_m, 0.0, 0.0

            t_to_stop = -initial_velocity_ms / driving_accel_ms2
            if t <= t_to_stop:
                v = initial_velocity_ms + driving_accel_ms2 * t
                x = initial_position_m + initial_velocity_ms * t + 0.5 * driving_accel_ms2 * (t ** 2)
                return x, max(0.0, v), driving_accel_ms2
            else:
                x_stop = (
                    initial_position_m
                    + initial_velocity_ms * t_to_stop
                    + 0.5 * driving_accel_ms2 * (t_to_stop ** 2)
                )
                return x_stop, 0.0, 0.0

        else:
            x = initial_position_m + initial_velocity_ms * t
            return x, initial_velocity_ms, 0.0

    # 4. Generate trajectory sampling with exact endpoints
    sample_times = []
    if duration_s == 0.0:
        sample_times = [0.0]
    else:
        current_t = 0.0
        epsilon = 1e-9
        while current_t < duration_s - epsilon:
            sample_times.append(current_t)
            current_t += time_step_s
        if not sample_times or sample_times[-1] < duration_s - epsilon:
            sample_times.append(duration_s)
        else:
            sample_times[-1] = duration_s

    trajectory = []
    for t in sample_times:
        pos, vel, acc = get_motion_state(t)
        disp = pos - initial_position_m
        rotations = disp / wheel_circumference_m if wheel_circumference_m > 0 else 0.0
        wheel_rpm = (
            (vel / wheel_radius_m) * (60.0 / (2.0 * math.pi))
            if wheel_radius_m > 0
            else 0.0
        )

        trajectory.append({
            "time_s": round(t, 3),
            "position_m": round(pos, 3),
            "velocity_ms": round(vel, 3),
            "acceleration_ms2": round(acc, 3),
            "wheel_rotations": round(rotations, 3),
            "wheel_rpm": round(wheel_rpm, 3),
        })

    # 5. Compile summary outputs
    final_pos, final_vel, final_acc = get_motion_state(duration_s)
    total_distance_m = final_pos - initial_position_m
    total_rotations = (
        total_distance_m / wheel_circumference_m if wheel_circumference_m > 0 else 0.0
    )
    final_wheel_rpm = (
        (final_vel / wheel_radius_m) * (60.0 / (2.0 * math.pi))
        if wheel_radius_m > 0
        else 0.0
    )

    # Evaluate whether top speed was actually reached during duration_s
    if initial_velocity_ms == top_speed_ms:
        top_speed_reached = True
        time_to_top_speed_s = 0.0
    elif initial_velocity_ms < top_speed_ms:
        if net_force_n > 0.0 and driving_accel_ms2 > 0.0:
            t_to_top = (top_speed_ms - initial_velocity_ms) / driving_accel_ms2
            top_speed_reached = duration_s >= t_to_top
            time_to_top_speed_s = round(t_to_top, 3) if top_speed_reached else None
        else:
            top_speed_reached = False
            time_to_top_speed_s = None
    else:
        # initial_velocity_ms > top_speed_ms (overspeed)
        if opposing_accel_ms2 < 0.0:
            t_to_top = (top_speed_ms - initial_velocity_ms) / opposing_accel_ms2
            top_speed_reached = duration_s >= t_to_top
            time_to_top_speed_s = round(t_to_top, 3) if top_speed_reached else None
        else:
            top_speed_reached = False
            time_to_top_speed_s = None

    return {
        "duration_s": round(duration_s, 3),
        "time_step_s": round(time_step_s, 3),
        "initial_velocity_ms": round(initial_velocity_ms, 3),
        "initial_position_m": round(initial_position_m, 3),
        "final_position_m": round(final_pos, 3),
        "distance_traveled_m": round(total_distance_m, 3),
        "final_velocity_ms": round(final_vel, 3),
        "final_velocity_kmh": round(final_vel * 3.6, 3),
        "final_acceleration_ms2": round(final_acc, 3),
        "top_speed_reached": top_speed_reached,
        "time_to_top_speed_s": time_to_top_speed_s,
        "wheel_radius_m": round(wheel_radius_m, 3),
        "wheel_rotations": round(total_rotations, 3),
        "wheel_rotation_deg": round(total_rotations * 360.0, 2),
        "wheel_rotation_rad": round(
            total_distance_m / wheel_radius_m if wheel_radius_m > 0 else 0.0, 3
        ),
        "final_wheel_rpm": round(final_wheel_rpm, 3),
        "net_force_n": round(net_force_n, 3),
        "driving_force_n": round(driving_force_n, 3),
        "traction_limit_n": round(base_sim["traction_limit_n"], 3),
        "traction_limited": base_sim["traction_limited"],
        "gravity_resistance_n": round(gravity_resistance_n, 3),
        "slope_resistance_n": round(gravity_resistance_n, 3),
        "rolling_resistance_n": round(rolling_resistance_n, 3),
        "can_move": base_sim["can_move_under_model"],
        "motion_model": "piecewise_constant_acceleration",
        "trajectory": trajectory,
        "base_simulation": base_sim,
        "assumptions": [
            "Piecewise constant-acceleration approximation across driving, coasting, and cruising regimes",
            "Driving force limited by motor torque gearing or Coulomb traction limit",
            "Top speed bounded by no-load / operating wheel angular velocity",
            "Motor is assumed disengaged (freewheeling) during overspeed coast-down (v > top_speed)",
            "Overspeed deceleration is governed solely by opposing slope gravity and rolling resistances",
            "Deceleration applies when net resistance exceeds driving force until forward motion ceases",
            "Robot stops at zero velocity with no reverse rollback under this model (static holding assumed)",
            "Pure rolling contact assumed for wheel rotation (zero wheel slip)",
            "Trajectory samples capped at MAX_TRAJECTORY_SAMPLES to prevent memory exhaustion",
            "No aerodynamic drag or dynamic axle load transfer modeled",
        ],
    }


# Retain alias for flexibility
simulate_motion = simulate_robot_motion
