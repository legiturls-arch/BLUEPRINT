import math
import pytest

from physics_engine import (
    simulate_robot,
    simulate_robot_motion,
    MAX_TRAJECTORY_SAMPLES,
)


# Shared test input for a 2 kg robot on flat ground.
def create_flat_ground_result():
    return simulate_robot(
        total_mass_kg=2,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        slope_degrees=0
    )


def test_driving_force_calculation():
    # Traction limits the force below the torque-limited value.
    result = create_flat_ground_result()

    assert result["torque_limited_force_n"] == pytest.approx(17.0)
    assert result["traction_limit_n"] == pytest.approx(13.734)
    assert result["driving_force_n"] == pytest.approx(13.734)


def test_acceleration_calculation():
    # Acceleration equals net force divided by total mass.
    result = create_flat_ground_result()

    assert result["net_force_n"] == pytest.approx(13.145)
    assert result["theoretical_acceleration_ms2"] == pytest.approx(6.573)


def test_robot_can_move_on_flat_ground():
    # Confirm the model predicts positive net force.
    result = create_flat_ground_result()

    assert result["can_move_under_model"] is True


def test_invalid_mass_is_rejected():
    # Zero mass is physically invalid for this model.
    with pytest.raises(ValueError):
        simulate_robot(
            total_mass_kg=0,
            motor_torque_nm=0.5,
            motor_count=2,
            wheel_radius_m=0.05
        )

# ==========================================
# 6. Motor, battery and gear-ratio tests
# ==========================================

def test_battery_voltage_changes_estimated_motor_speed():
    """Lower voltage should reduce estimated no-load speed."""

    full_voltage = simulate_robot(
        total_mass_kg=2,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        motor_rpm=150,
        battery_voltage_v=12,
        motor_rated_voltage_v=12,
        motor_no_load_rpm=200,
        motor_stall_torque_nm=1,
    )

    lower_voltage = simulate_robot(
        total_mass_kg=2,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        motor_rpm=150,
        battery_voltage_v=6,
        motor_rated_voltage_v=12,
        motor_no_load_rpm=200,
        motor_stall_torque_nm=1,
    )

    assert full_voltage["motor_rpm"] == 150
    assert lower_voltage["motor_rpm"] == 100
    assert (
        lower_voltage["theoretical_wheel_speed_ms"]
        < full_voltage["theoretical_wheel_speed_ms"]
    )


def test_gear_ratio_changes_wheel_speed_and_torque():
    """A 5:1 reduction lowers wheel RPM and increases wheel torque."""

    result = simulate_robot(
        total_mass_kg=2,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        motor_rpm=25,
        battery_voltage_v=12,
        motor_rated_voltage_v=12,
        motor_no_load_rpm=100,
        motor_stall_torque_nm=1,
        gear_ratio=5,
    )

    assert result["wheel_rpm"] == 5
    assert result["estimated_motor_torque_nm"] == 0.75
    assert result["effective_torque_nm"] == 6.375
    assert result["torque_limited_force_n"] == 127.5


def test_motor_torque_decreases_as_rpm_increases():
    """The simplified DC motor curve predicts less torque at higher RPM."""

    low_speed = simulate_robot(
        total_mass_kg=2,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        motor_rpm=25,
        motor_rated_voltage_v=12,
        motor_no_load_rpm=100,
        motor_stall_torque_nm=1,
    )

    high_speed = simulate_robot(
        total_mass_kg=2,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        motor_rpm=75,
        motor_rated_voltage_v=12,
        motor_no_load_rpm=100,
        motor_stall_torque_nm=1,
    )

    assert low_speed["estimated_motor_torque_nm"] == 0.75
    assert high_speed["estimated_motor_torque_nm"] == 0.25
    assert (
        low_speed["estimated_motor_torque_nm"]
        > high_speed["estimated_motor_torque_nm"]
    )


def test_incomplete_motor_datasheet_is_rejected():
    """Datasheet mode must receive all three motor specifications."""

    with pytest.raises(ValueError, match="Provide"):
        simulate_robot(
            total_mass_kg=2,
            motor_torque_nm=0.5,
            motor_count=2,
            wheel_radius_m=0.05,
            motor_rated_voltage_v=12,
        )


# ============================================================
# 7. TIME-BASED MOTION TESTS (simulate_robot_motion)
# ============================================================

def test_motion_starts_from_rest_and_accelerates():
    """
    1. Acceleration derived from the exact physical force model:
       F_driving = min(F_torque, F_traction) = 13.734 N
       F_gravity = 0.0 N
       F_rolling = 0.03 * 19.62 = 0.589 N
       F_net = F_driving - F_gravity - F_rolling = 13.145 N
       a = F_net / mass = 13.145 / 2.0 = 6.5725 m/s^2
    """
    result = simulate_robot_motion(
        total_mass_kg=2.0,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        slope_degrees=0.0,
        initial_velocity_ms=0.0,
        duration_s=0.05,
        time_step_s=0.01,
    )

    top_speed = result["base_simulation"]["theoretical_wheel_speed_ms"]

    # Derive net force directly from reported force components
    expected_net_force = (
        result["driving_force_n"]
        - result["gravity_resistance_n"]
        - result["rolling_resistance_n"]
    )
    assert result["net_force_n"] == pytest.approx(expected_net_force, abs=1e-3)

    # Derive expected motion acceleration directly from net force / mass
    derived_accel = result["net_force_n"] / 2.0
    assert result["final_acceleration_ms2"] == pytest.approx(derived_accel, abs=1e-3)

    assert result["initial_velocity_ms"] == 0.0
    assert 0.0 < result["final_velocity_ms"] < top_speed
    assert result["top_speed_reached"] is False
    assert result["time_to_top_speed_s"] is None
    assert result["distance_traveled_m"] > 0.0
    assert result["wheel_rotations"] > 0.0


def test_motion_reaches_top_speed_and_cruises():
    """
    2. Over 2.0 s (> time to top speed ~0.08 s), robot reaches top speed and cruises.
       Acceleration drops to 0.0 m/s^2 once top speed is attained.
    """
    result = simulate_robot_motion(
        total_mass_kg=2.0,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        slope_degrees=0.0,
        initial_velocity_ms=0.0,
        duration_s=2.0,
        time_step_s=0.1,
    )

    top_speed = result["base_simulation"]["theoretical_wheel_speed_ms"]

    assert result["top_speed_reached"] is True
    assert result["time_to_top_speed_s"] is not None
    assert 0.0 < result["time_to_top_speed_s"] < 2.0
    assert result["final_velocity_ms"] == pytest.approx(top_speed, abs=1e-3)
    assert result["final_velocity_kmh"] == pytest.approx(top_speed * 3.6, abs=1e-3)
    assert result["final_acceleration_ms2"] == 0.0

    # Verify steady-state cruise across trajectory samples
    for point in result["trajectory"]:
        if point["time_s"] >= result["time_to_top_speed_s"]:
            assert point["velocity_ms"] == pytest.approx(top_speed, abs=1e-3)
            assert point["acceleration_ms2"] == 0.0


def test_motion_overspeed_starting_at_5ms_coasts_down_without_clamping():
    """
    3. Starting at 5.0 m/s (top speed ~0.524 m/s).
       Coast-down takes ~15.21 s.
       At duration_s = 2.0 s, robot must still be in overspeed (~4.411 m/s).
       Confirms velocity does not artificially clamp to top speed.
    """
    result = simulate_robot_motion(
        total_mass_kg=2.0,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        initial_velocity_ms=5.0,
        duration_s=2.0,
        time_step_s=0.1,
    )

    top_speed = result["base_simulation"]["theoretical_wheel_speed_ms"]
    opposing_accel = -(result["gravity_resistance_n"] + result["rolling_resistance_n"]) / 2.0
    expected_vel = 5.0 + opposing_accel * 2.0

    assert result["final_velocity_ms"] == pytest.approx(expected_vel, abs=1e-2)
    assert result["final_velocity_ms"] > top_speed
    assert result["top_speed_reached"] is False
    assert result["time_to_top_speed_s"] is None


def test_motion_overspeed_starting_at_2ms_reaches_top_speed_and_cruises():
    """
    4. Starting at 2.0 m/s (top speed ~0.524 m/s).
       Coast-down takes ~5.015 s.
       At duration_s = 7.0 s (> 5.015 s), robot reaches top speed and cruises.
       top_speed_reached is True and final acceleration is 0.0.
    """
    result = simulate_robot_motion(
        total_mass_kg=2.0,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        initial_velocity_ms=2.0,
        duration_s=7.0,
        time_step_s=0.1,
    )

    top_speed = result["base_simulation"]["theoretical_wheel_speed_ms"]
    opposing_accel = -(result["gravity_resistance_n"] + result["rolling_resistance_n"]) / 2.0
    expected_t_to_top = (top_speed - 2.0) / opposing_accel

    assert result["top_speed_reached"] is True
    assert result["time_to_top_speed_s"] == pytest.approx(expected_t_to_top, abs=1e-2)
    assert result["final_velocity_ms"] == pytest.approx(top_speed, abs=1e-3)
    assert result["final_acceleration_ms2"] == 0.0


def test_motion_negative_net_force_stops_without_reversing():
    """
    5. Robot with initial_velocity_ms = 1.0 on a steep 45° slope with insufficient motor torque.
       - can_move is False: motor power cannot overcome gravity + rolling resistance.
       - Robot coasts forward while decelerating and stops at 0.0 m/s (~0.16 s).
       - Velocity stays at 0.0 m/s (does not go negative).
       - Robot does not roll backward downhill: position >= initial_position for all samples.
    """
    result = simulate_robot_motion(
        total_mass_kg=2.0,
        motor_torque_nm=0.1,
        motor_count=1,
        wheel_radius_m=0.05,
        slope_degrees=45.0,
        initial_velocity_ms=1.0,
        initial_position_m=2.0,
        duration_s=5.0,
        time_step_s=0.1,
    )

    assert result["can_move"] is False
    assert result["final_velocity_ms"] == 0.0
    assert result["final_acceleration_ms2"] == 0.0
    assert result["final_position_m"] >= 2.0

    for point in result["trajectory"]:
        assert point["velocity_ms"] >= 0.0
        assert point["position_m"] >= 2.0


def test_motion_zero_duration_simulation():
    """
    6. duration_s = 0.0 must return a single sample at t = 0.0 without divide-by-zero errors.
    """
    result = simulate_robot_motion(
        total_mass_kg=2.0,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        initial_velocity_ms=1.5,
        initial_position_m=3.0,
        duration_s=0.0,
    )

    assert result["duration_s"] == 0.0
    assert result["final_position_m"] == 3.0
    assert result["distance_traveled_m"] == 0.0
    assert result["final_velocity_ms"] == 1.5
    assert result["wheel_rotations"] == 0.0
    assert len(result["trajectory"]) == 1
    assert result["trajectory"][0]["time_s"] == 0.0
    assert result["trajectory"][0]["position_m"] == 3.0
    assert result["trajectory"][0]["velocity_ms"] == 1.5


def test_motion_exact_trajectory_sample_counts():
    """
    7. Exact sample count checks:
       - duration = 1.0, step = 0.2 -> exactly 6 samples [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
       - duration = 1.0, step = 0.3 -> exactly 5 samples [0.0, 0.3, 0.6, 0.9, 1.0]
       - duration = 19.99, step = 0.01 -> exactly 2000 samples (boundary allowed)
       - duration = 20.0, step = 0.01 -> 2001 samples (safety limit exceeded, raises ValueError)
    """
    res_even = simulate_robot_motion(
        total_mass_kg=2.0,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        duration_s=1.0,
        time_step_s=0.2,
    )
    assert len(res_even["trajectory"]) == 6
    assert [p["time_s"] for p in res_even["trajectory"]] == [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

    res_uneven = simulate_robot_motion(
        total_mass_kg=2.0,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        duration_s=1.0,
        time_step_s=0.3,
    )
    assert len(res_uneven["trajectory"]) == 5
    assert [p["time_s"] for p in res_uneven["trajectory"]] == [0.0, 0.3, 0.6, 0.9, 1.0]

    # Sample limit boundary: 2000 samples succeeds
    res_limit_ok = simulate_robot_motion(
        total_mass_kg=2.0,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        duration_s=19.99,
        time_step_s=0.01,
    )
    assert len(res_limit_ok["trajectory"]) == MAX_TRAJECTORY_SAMPLES

    # Sample limit boundary: 2001 samples raises ValueError
    with pytest.raises(ValueError, match="safety limit of 2000"):
        simulate_robot_motion(
            total_mass_kg=2.0,
            motor_torque_nm=0.5,
            motor_count=2,
            wheel_radius_m=0.05,
            duration_s=20.0,
            time_step_s=0.01,
        )


def test_motion_numeric_validation_nan_inf_bool():
    """
    8. Explicit rejection of NaN, infinity, and boolean values across motion inputs.
    """
    base_kwargs = {
        "total_mass_kg": 2.0,
        "motor_torque_nm": 0.5,
        "motor_count": 2,
        "wheel_radius_m": 0.05,
    }

    invalid_numeric_values = [
        float("nan"),
        float("inf"),
        float("-inf"),
        True,
        False,
    ]

    for bad_val in invalid_numeric_values:
        with pytest.raises(ValueError, match="duration_s"):
            simulate_robot_motion(**base_kwargs, duration_s=bad_val)

        with pytest.raises(ValueError, match="time_step_s"):
            simulate_robot_motion(**base_kwargs, time_step_s=bad_val)

        with pytest.raises(ValueError, match="initial_velocity_ms"):
            simulate_robot_motion(**base_kwargs, initial_velocity_ms=bad_val)

        with pytest.raises(ValueError, match="initial_position_m"):
            simulate_robot_motion(**base_kwargs, initial_position_m=bad_val)


def test_motion_forwarded_parameter_validation():
    """
    9. Explicit rejection of invalid motor count, torque, and wheel radius via forwarded validation.
    """
    base_kwargs = {
        "total_mass_kg": 2.0,
        "motor_torque_nm": 0.5,
        "motor_count": 2,
        "wheel_radius_m": 0.05,
    }

    # Invalid motor count: 0 (< 1), 21 (> 20), 2.5 (non-int), True (bool)
    for bad_count in [0, 21, 2.5, True]:
        kwargs = dict(base_kwargs, motor_count=bad_count)
        with pytest.raises(ValueError, match="motor_count"):
            simulate_robot_motion(**kwargs)

    # Invalid motor torque: -0.1 (< 0), 10.1 (> MAX_MOTOR_TORQUE_NM 10.0)
    for bad_torque in [-0.1, 10.1]:
        kwargs = dict(base_kwargs, motor_torque_nm=bad_torque)
        with pytest.raises(ValueError, match="motor_torque_nm"):
            simulate_robot_motion(**kwargs)

    # Invalid wheel radius: 0.004 (< MIN 0.005), 0.51 (> MAX 0.5)
    for bad_radius in [0.004, 0.51]:
        kwargs = dict(base_kwargs, wheel_radius_m=bad_radius)
        with pytest.raises(ValueError, match="wheel_radius_m"):
            simulate_robot_motion(**kwargs)


def test_motion_time_step_boundaries():
    """
    10. Enforces minimum (0.001 s) and maximum (10.0 s) allowed time steps.
    """
    base_kwargs = {
        "total_mass_kg": 2.0,
        "motor_torque_nm": 0.5,
        "motor_count": 2,
        "wheel_radius_m": 0.05,
    }

    # Minimum boundary
    simulate_robot_motion(**base_kwargs, time_step_s=0.001, duration_s=0.1)
    with pytest.raises(ValueError, match="time_step_s"):
        simulate_robot_motion(**base_kwargs, time_step_s=0.0009, duration_s=0.1)

    # Maximum boundary
    simulate_robot_motion(**base_kwargs, time_step_s=10.0, duration_s=10.0)
    with pytest.raises(ValueError, match="time_step_s"):
        simulate_robot_motion(**base_kwargs, time_step_s=10.001, duration_s=10.0)


def test_motion_preserves_simulate_robot_invariants():
    """
    11. Verify that simulate_robot() results remain identical and unmutated.
    """
    base_res = simulate_robot(
        total_mass_kg=2.0,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        slope_degrees=0.0,
    )

    motion_res = simulate_robot_motion(
        total_mass_kg=2.0,
        motor_torque_nm=0.5,
        motor_count=2,
        wheel_radius_m=0.05,
        slope_degrees=0.0,
        duration_s=1.0,
    )

    # Invariants from original tests in test_physics_engine.py
    assert base_res["torque_limited_force_n"] == pytest.approx(17.0)
    assert base_res["driving_force_n"] == pytest.approx(13.734)
    assert base_res["net_force_n"] == pytest.approx(13.145)
    assert base_res["theoretical_acceleration_ms2"] == pytest.approx(6.573)
    assert base_res["can_move_under_model"] is True

    # Exact matching of nested base_simulation
    assert motion_res["base_simulation"] == base_res
