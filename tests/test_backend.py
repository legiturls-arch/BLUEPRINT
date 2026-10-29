
# ============================================================
# BLUEPRINT - BACKEND TESTS
# Purpose: Check API routes, component library, physics,
# engineering analysis, invalid inputs, and edge cases.
# ============================================================

# Import pytest for fixtures, parameterized tests, and approx().
import pytest

# Test FastAPI routes without starting a separate server.
from fastapi.testclient import TestClient

# Import the app and functions being tested.
from app import app
from engineering_analyzer import analyze_simulation
from physics_engine import simulate_robot


# ============================================================
# 1. TEST FIXTURE - REUSABLE API CLIENT
# ============================================================

@pytest.fixture
def client():
    # Automatically open and close the test client for each test.
    with TestClient(app) as test_client:
        yield test_client


# ============================================================
# 2. HOME ROUTE TEST
# ============================================================

def test_home_route(client):
    # Check that the main API route is running.
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to BLUEPRINT Virtual Engineering Lab",
        "status": "running",
    }


# ============================================================
# 3. HEALTH ROUTE TEST
# ============================================================

def test_health_route(client):
    # Check that the health endpoint returns OK.
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ============================================================
# 4. COMPONENT LIBRARY TEST
# ============================================================

def test_components_route(client):
    # Request all available engineering components.
    response = client.get("/api/components")

    assert response.status_code == 200
    components = response.json()["components"]

    # The current unified component library contains 21 items.
    assert len(components) == 21

    # Find the basic motor without depending on its list position.
    motor = next(
        component
        for component in components
        if component["id"] == "motor_basic"
    )

    # Check the motor's main properties.
    assert motor["name"] == "Basic DC Motor"
    assert motor["category"] == "actuator"
    assert motor["mass_kg"] == 0.2
    assert motor["max_torque_nm"] == 0.5

    # Check the motor's additional metadata.
    assert motor["description"] == "Starter motor for a small robot."
    assert motor["tags"] == ["motor", "dc", "robotics"]
    assert motor["library"] == "engineering"
    assert motor["spec_status"] == "prototype"


# ============================================================
# 5. VALID ROBOT SIMULATION TEST
# ============================================================

def test_simulate_route_with_valid_input(client):

    # Send a valid robot configuration to the simulation API.
    response = client.post(
        "/api/simulate",
        json={
            "total_mass_kg": 2,
            "motor_torque_nm": 0.5,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "slope_degrees": 0,
        },
    )

    # A valid configuration should return HTTP 200.
    assert response.status_code == 200

    body = response.json()

    # Check the main simulation response.
    assert body["status"] == "success"
    assert body["simulation"]["total_motor_torque_nm"] == 1.0

    # Traction limits the driving force to approximately 13.734 N.
    assert body["simulation"]["driving_force_n"] == pytest.approx(13.734)

    # The model predicts that this robot can move.
    assert body["simulation"]["can_move_under_model"] is True

    # Engineering analysis should include warnings and suggestions.
    assert "warnings" in body["engineering_analysis"]
    assert "suggestions" in body["engineering_analysis"]


# ============================================================
# 6. INVALID INPUT TESTS
# ============================================================

@pytest.mark.parametrize(
    "overrides",
    [
        # Basic invalid inputs.
        {"total_mass_kg": 0},
        {"motor_torque_nm": -0.1},
        {"motor_count": 0},
        {"motor_count": 21},
        {"wheel_radius_m": 0},

        # Inputs exceeding the initial small-robot model limits.
        {"total_mass_kg": 100.1},
        {"motor_torque_nm": 10.1},
        {"wheel_radius_m": 0.501},
    ],
    ids=[
        "zero-mass",
        "negative-torque",
        "zero-motors",
        "too-many-motors",
        "zero-wheel-radius",
        "mass-above-model-limit",
        "torque-above-model-limit",
        "wheel-radius-above-model-limit",
    ],
)
def test_simulate_route_rejects_invalid_input(client, overrides):
    # Start with a valid configuration.
    request_data = {
        "total_mass_kg": 2,
        "motor_torque_nm": 0.5,
        "motor_count": 2,
        "wheel_radius_m": 0.05,
        "slope_degrees": 0,
    }

    # Replace one value with the invalid value for this test.
    request_data.update(overrides)

   
    # Send the request and save the response.
    response = client.post("/api/simulate", json=request_data)

    # Check that invalid input is rejected.
    assert response.status_code in (400, 422)
    assert "detail" in response.json()


# ============================================================
# 7. NEAR-ZERO FORCE TESTS
# ============================================================

@pytest.mark.parametrize(
    ("motor_torque_nm", "expected_can_move"),
    [
        # Slightly positive net force.
        (0.304, True),

        # Slightly negative net force.
        (0.303, False),
    ],
    ids=[
        "slightly-positive-net-force",
        "slightly-negative-net-force",
    ],
)
def test_near_zero_force_result_and_analysis_are_consistent(
    motor_torque_nm, expected_can_move
):
    # Simulate a 1 kg robot on a 30-degree slope.
    simulation = simulate_robot(
        total_mass_kg=1,
        motor_torque_nm=motor_torque_nm,
        motor_count=1,
        wheel_radius_m=0.05,
        slope_degrees=30,
    )

    # Analyze the same result returned by the physics engine.
    analysis = analyze_simulation(simulation)

    # Determine movement from the calculated net force.
    force_says_robot_can_move = simulation["net_force_n"] > 0

    # Check whether the analyzer warns that the robot may not move.
    analysis_says_robot_cannot_move = any(
        "may not move" in warning.lower()
        for warning in analysis["warnings"]
    )

    # Collect any disagreements between simulation and analysis.
    contradictions = []

    if simulation["can_move_under_model"] is not expected_can_move:
        contradictions.append("movement flag is unexpected")

    if force_says_robot_can_move is not expected_can_move:
        contradictions.append(
            f"net force is {simulation['net_force_n']}"
        )

    if analysis_says_robot_cannot_move is not (not expected_can_move):
        contradictions.append(
            "analyzer warning conflicts with movement flag"
        )

    # The simulation and analyzer must agree.
    assert not contradictions, "; ".join(contradictions)


# ============================================================
# 8. HIGH-ACCELERATION WARNING TESTS
# ============================================================

@pytest.mark.parametrize(
    ("acceleration", "expects_warning"),
    [
        # Exactly 5.0 m/s² should not trigger the warning.
        (5.0, False),

        # Above 5.0 m/s² should trigger the warning.
        (5.001, True),
    ],
)
def test_analyzer_acceleration_warning_threshold(
    acceleration, expects_warning
):
    # Supply the fields needed for this focused analyzer test.
    analysis = analyze_simulation(
        {
            "net_force_n": 1.0,
            "theoretical_acceleration_ms2": acceleration,
        }
    )

    # Search for the high-acceleration warning.
    high_acceleration_warning = any(
        "acceleration is high" in warning.lower()
        for warning in analysis["warnings"]
    )

    # Compare the actual warning with the expected result.
    assert high_acceleration_warning is expects_warning


# ============================================================
# 9. EXTREME NUMERIC INPUT TEST
# ============================================================

def test_simulate_route_returns_controlled_error_for_extreme_numeric_input():
    # Prevent server exceptions from stopping this test immediately.
    client = TestClient(app, raise_server_exceptions=False)

    # Send an extremely large motor torque.
    response = client.post(
        "/api/simulate",
        json={
            "total_mass_kg": 1,
            "motor_torque_nm": 1e308,
            "motor_count": 20,
            "wheel_radius_m": 0.05,
            "slope_degrees": 0,
        },
    )

    # Try to read the error response as JSON.
    try:
        body = response.json()
    except ValueError:
        body = None

    # The API should return a controlled 400/422 JSON error.
    assert (
        response.status_code in (400, 422)
        and isinstance(body, dict)
        and "detail" in body
    ), (
        "Expected a controlled 400/422 JSON validation error, "
        f"got status {response.status_code} with body {response.text!r}"
    )

def test_simulation_warns_when_configured_robot_has_no_battery(client):
    response = client.post(
        "/api/simulate",
        json={
            "total_mass_kg": 2,
            "motor_torque_nm": 0.5,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "slope_degrees": 0,
            "installed_component_ids": [
                "motor_basic",
                "wheel_basic",
                "chassis_basic",
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    analysis = data["engineering_analysis"]

    assert any(
        "battery" in warning.lower()
        for warning in analysis["warnings"]
    )
    assert any(
        "battery" in suggestion.lower()
        for suggestion in analysis["suggestions"]
    )
def test_simulation_passes_battery_presence_check_when_battery_installed(client):
    response = client.post(
        "/api/simulate",
        json={
            "total_mass_kg": 2,
            "motor_torque_nm": 0.5,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "slope_degrees": 0,
            "installed_component_ids": [
                "motor_basic",
                "wheel_basic",
                "chassis_basic",
                "battery_basic",
            ],
        },
    )

    assert response.status_code == 200

    analysis = response.json()["engineering_analysis"]

    battery_check = next(
        check
        for check in analysis["checks"]
        if check["name"] == "battery_presence"
    )

    assert battery_check["status"] == "pass"

    assert not any(
        "battery component is missing" in warning.lower()
        for warning in analysis["warnings"]
    )


# ============================================================
# 10. TIME-BASED MOTION SIMULATION ROUTE TESTS
# ============================================================

def test_simulate_motion_route_with_valid_input(client):
    """Verify POST /api/simulate-motion returns complete motion results."""
    response = client.post(
        "/api/simulate-motion",
        json={
            "total_mass_kg": 2.0,
            "motor_torque_nm": 0.5,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "slope_degrees": 0.0,
            "initial_velocity_ms": 0.0,
            "initial_position_m": 0.0,
            "duration_s": 1.0,
            "time_step_s": 0.1,
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "success"
    assert body["duration_s"] == 1.0
    assert body["time_step_s"] == 0.1
    assert body["initial_velocity_ms"] == 0.0
    assert body["initial_position_m"] == 0.0
    assert body["final_velocity_ms"] > 0.0
    assert body["final_velocity_kmh"] == pytest.approx(
        body["final_velocity_ms"] * 3.6, abs=1e-3
    )
    assert body["distance_traveled_m"] > 0.0
    assert body["final_position_m"] == pytest.approx(
        body["initial_position_m"] + body["distance_traveled_m"], abs=1e-3
    )
    assert body["wheel_rotations"] > 0.0
    assert body["final_wheel_rpm"] > 0.0
    assert body["can_move"] is True

    # Trajectory samples verification
    assert "trajectory" in body
    trajectory = body["trajectory"]
    assert len(trajectory) == 11
    assert trajectory[0]["time_s"] == 0.0
    assert trajectory[0]["position_m"] == 0.0
    assert trajectory[-1]["time_s"] == 1.0

    for point in trajectory:
        assert "time_s" in point
        assert "position_m" in point
        assert "velocity_ms" in point
        assert "acceleration_ms2" in point
        assert "wheel_rotations" in point
        assert "wheel_rpm" in point

    # Simulation assumptions verification
    assert "assumptions" in body
    assert isinstance(body["assumptions"], list)
    assert len(body["assumptions"]) > 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"total_mass_kg": 0},
        {"total_mass_kg": -1.0},
        {"total_mass_kg": 100.1},
        {"motor_torque_nm": -0.1},
        {"motor_torque_nm": 10.1},
        {"motor_count": 0},
        {"motor_count": 21},
        {"wheel_radius_m": 0.004},
        {"wheel_radius_m": 0.51},
        {"slope_degrees": -1},
        {"slope_degrees": 90},
        {"initial_velocity_ms": -1.0},
        {"initial_position_m": -0.5},
        {"duration_s": -0.1},
        {"duration_s": 3601.0},
        {"time_step_s": 0.0009},
        {"time_step_s": 10.001},
        {"total_mass_kg": True},
        {"motor_count": False},
        {"total_mass_kg": "invalid-string"},
    ],
    ids=[
        "zero-mass",
        "negative-mass",
        "mass-above-limit",
        "negative-torque",
        "torque-above-limit",
        "zero-motors",
        "too-many-motors",
        "wheel-radius-below-limit",
        "wheel-radius-above-limit",
        "negative-slope",
        "slope-above-limit",
        "negative-initial-velocity",
        "negative-initial-position",
        "negative-duration",
        "duration-above-limit",
        "time-step-below-limit",
        "time-step-above-limit",
        "bool-mass",
        "bool-motor-count",
        "string-mass",
    ],
)
def test_simulate_motion_route_rejects_invalid_inputs(client, overrides):
    """Verify invalid inputs return controlled HTTP 422 with JSON details."""
    payload = {
        "total_mass_kg": 2.0,
        "motor_torque_nm": 0.5,
        "motor_count": 2,
        "wheel_radius_m": 0.05,
        "slope_degrees": 0.0,
        "initial_velocity_ms": 0.0,
        "initial_position_m": 0.0,
        "duration_s": 1.0,
        "time_step_s": 0.1,
    }
    payload.update(overrides)

    response = client.post("/api/simulate-motion", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body


def test_simulate_motion_route_zero_duration(client):
    """Verify zero-duration simulation returns single trajectory sample at t=0."""
    response = client.post(
        "/api/simulate-motion",
        json={
            "total_mass_kg": 2.0,
            "motor_torque_nm": 0.5,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "slope_degrees": 0.0,
            "initial_velocity_ms": 1.5,
            "initial_position_m": 3.0,
            "duration_s": 0.0,
            "time_step_s": 0.1,
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "success"
    assert body["duration_s"] == 0.0
    assert body["final_position_m"] == 3.0
    assert body["distance_traveled_m"] == 0.0
    assert body["final_velocity_ms"] == 1.5
    assert body["wheel_rotations"] == 0.0
    assert len(body["trajectory"]) == 1
    assert body["trajectory"][0]["time_s"] == 0.0
    assert body["trajectory"][0]["position_m"] == 3.0
    assert body["trajectory"][0]["velocity_ms"] == 1.5


def test_simulate_motion_route_excessive_trajectory_limit(client):
    """Verify requests exceeding MAX_TRAJECTORY_SAMPLES return controlled HTTP 422."""
    # Boundary: 2000 samples succeeds
    allowed_response = client.post(
        "/api/simulate-motion",
        json={
            "total_mass_kg": 2.0,
            "motor_torque_nm": 0.5,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "duration_s": 19.99,
            "time_step_s": 0.01,
        },
    )
    assert allowed_response.status_code == 200
    assert len(allowed_response.json()["trajectory"]) == 2000

    # Exceeding boundary: 2001 samples returns 422
    excessive_response = client.post(
        "/api/simulate-motion",
        json={
            "total_mass_kg": 2.0,
            "motor_torque_nm": 0.5,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "duration_s": 20.0,
            "time_step_s": 0.01,
        },
    )
    assert excessive_response.status_code == 422
    body = excessive_response.json()
    assert isinstance(body, dict)
    assert "detail" in body


def test_simulate_motion_route_valid_catalogue_request(client):
    """Verify valid catalogue-based request loads verified motor datasheet and simulates."""
    response = client.post(
        "/api/simulate-motion",
        json={
            "total_mass_kg": 2.0,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "motor_component_id": "motor_geared",
            "duration_s": 2.0,
            "time_step_s": 0.1,
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "success"
    assert "selected_motor" in body
    assert body["selected_motor"]["id"] == "motor_geared"
    assert body["selected_motor"]["spec_status"] == "verified"
    assert body["duration_s"] == 2.0
    assert body["final_velocity_ms"] > 0.0
    assert body["distance_traveled_m"] > 0.0
    assert len(body["trajectory"]) == 21


def test_simulate_motion_route_supported_custom_motor_requests(client):
    """Verify custom motor parameters via direct torque and custom datasheet values."""
    # Custom direct torque
    response_torque = client.post(
        "/api/simulate-motion",
        json={
            "total_mass_kg": 2.0,
            "motor_torque_nm": 0.75,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "duration_s": 1.0,
            "time_step_s": 0.1,
        },
    )
    assert response_torque.status_code == 200
    assert response_torque.json()["status"] == "success"

    # Custom datasheet specs
    response_datasheet = client.post(
        "/api/simulate-motion",
        json={
            "total_mass_kg": 2.0,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "motor_rated_voltage_v": 12.0,
            "motor_no_load_rpm": 250.0,
            "motor_stall_torque_nm": 0.8,
            "duration_s": 1.0,
            "time_step_s": 0.1,
        },
    )
    assert response_datasheet.status_code == 200
    assert response_datasheet.json()["status"] == "success"


def test_simulate_motion_route_rejects_duplicate_datasheet_fields(client):
    """Verify supplying datasheet fields alongside motor_component_id returns HTTP 422."""
    response = client.post(
        "/api/simulate-motion",
        json={
            "total_mass_kg": 2.0,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "motor_component_id": "motor_geared",
            "motor_rated_voltage_v": 12.0,
            "motor_no_load_rpm": 200.0,
            "motor_stall_torque_nm": 1.0,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    detail_str = str(body["detail"])
    assert "Do not provide the same datasheet fields separately" in detail_str


def test_simulate_motion_route_rejects_invalid_component_ids(client):
    """Verify nonexistent, non-actuator, and unverified components return controlled HTTP 422."""
    # Nonexistent component
    res_nonexistent = client.post(
        "/api/simulate-motion",
        json={
            "total_mass_kg": 2.0,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "motor_component_id": "nonexistent_motor_xyz",
        },
    )
    assert res_nonexistent.status_code == 422
    assert "not found" in str(res_nonexistent.json()["detail"])

    # Non-actuator component (wheel_basic)
    res_non_actuator = client.post(
        "/api/simulate-motion",
        json={
            "total_mass_kg": 2.0,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "motor_component_id": "wheel_basic",
        },
    )
    assert res_non_actuator.status_code == 422
    assert "not an actuator" in str(res_non_actuator.json()["detail"])

    # Unverified prototype motor (motor_basic)
    res_unverified = client.post(
        "/api/simulate-motion",
        json={
            "total_mass_kg": 2.0,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "motor_component_id": "motor_basic",
        },
    )
    assert res_unverified.status_code == 422
    assert (
        "not marked as verified" in str(res_unverified.json()["detail"])
        or "incomplete" in str(res_unverified.json()["detail"])
    )


def test_simulate_motion_route_with_installed_components(client):
    """Verify installed component IDs trigger battery presence checks in engineering analysis."""
    response = client.post(
        "/api/simulate-motion",
        json={
            "total_mass_kg": 2.0,
            "motor_torque_nm": 0.5,
            "motor_count": 2,
            "wheel_radius_m": 0.05,
            "installed_component_ids": [
                "motor_basic",
                "wheel_basic",
                "chassis_basic",
                "battery_basic",
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "engineering_analysis" in body
    analysis = body["engineering_analysis"]
    battery_check = next(
        c for c in analysis["checks"] if c["name"] == "battery_presence"
    )
    assert battery_check["status"] == "pass"


def test_simulate_motion_route_extreme_numeric_input():
    """Verify extreme numeric input returns controlled HTTP 422 without server error."""
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/simulate-motion",
        json={
            "total_mass_kg": 1,
            "motor_torque_nm": 1e308,
            "motor_count": 20,
            "wheel_radius_m": 0.05,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert isinstance(body, dict)
    assert "detail" in body
