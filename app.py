# ==========================================
# BLUEPRINT - Virtual Engineering Lab API
# ==========================================

import math
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from components import get_components
from physics_engine import (
    simulate_robot,
    simulate_robot_motion,
    MAX_TRAJECTORY_SAMPLES,
)
from engineering_analyzer import analyze_simulation
from robot_testing import (
    run_endurance_test,
    run_environment_test,
    run_payload_test,
    run_structural_test,
    run_terrain_test,
    test_campaigns,
)


app = FastAPI(
    title="BLUEPRINT - Virtual Engineering Lab",
    description="AI-assisted engineering simulation platform",
    version="0.4.0",
)

# The SHA-256 source in script-src authorizes only builder.html's import map.
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "form-action 'self'; "
        "script-src 'self' https://www.gstatic.com https://cdn.jsdelivr.net "
        "https://apis.google.com "
        "'sha256-JdScvVUA/cDmBCFIYLh+HW5jutDgoIZymbVEtFkzU6k='; "
        "style-src 'self'; "
        "img-src 'self' https://www.gstatic.com https://www.google.com; "
        "font-src 'self'; "
        "connect-src 'self' https://identitytoolkit.googleapis.com "
        "https://securetoken.googleapis.com https://firebaseinstallations.googleapis.com "
        "https://www.googleapis.com https://apis.google.com "
        "https://www.google.com https://www.recaptcha.net; "
        "frame-src 'self' https://blueprint-266f8.firebaseapp.com "
        "https://accounts.google.com https://www.google.com "
        "https://recaptcha.google.com https://www.recaptcha.net; "
        "worker-src 'self' blob:; "
        "manifest-src 'self'; "
        "script-src-attr 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Permissions-Policy": (
        "accelerometer=(), autoplay=(), camera=(), "
        "display-capture=(), geolocation=(), gyroscope=(), magnetometer=(), "
        "microphone=(), midi=(), payment=(), usb=(), xr-spatial-tracking=(), "
        "fullscreen=(self)"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response


# ------------------------------------------
# 1. Basic routes
# ------------------------------------------

@app.get("/")
def home():
    return RedirectResponse(url="/ui/index.html")


@app.get("/health")
def health_check():
    return {"status": "ok"}


# ------------------------------------------
# 2. Component library
# ------------------------------------------

@app.get("/api/components")
def list_components():
    return {"components": get_components()}


def find_motor_component(component_id: str) -> dict:
    """Find a motor and reject incomplete or unverified specifications."""

    component = next(
        (
            item
            for item in get_components()
            if item.get("id") == component_id
        ),
        None,
    )

    if component is None:
        raise HTTPException(
            status_code=404,
            detail=f"Component '{component_id}' was not found.",
        )

    if component.get("category") != "actuator":
        raise HTTPException(
            status_code=400,
            detail=f"Component '{component_id}' is not an actuator.",
        )

    required_fields = (
        "rated_voltage_v",
        "no_load_rpm",
        "stall_torque_nm",
    )

    missing = [
        field
        for field in required_fields
        if component.get(field) is None
    ]

    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Motor datasheet specifications are incomplete.",
                "component_id": component_id,
                "missing_fields": missing,
                "spec_status": component.get("spec_status", "unknown"),
            },
        )

    if component.get("spec_status") != "verified":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Motor '{component_id}' is not marked as verified. "
                "Verify its specifications against the manufacturer's datasheet."
            ),
        )

    return component


# ------------------------------------------
# 3. Simulation input validation
# ------------------------------------------

class SimulationRequest(BaseModel):
    total_mass_kg: float = Field(
        gt=0, le=100, allow_inf_nan=False
    )
    motor_torque_nm: float = Field(
        ge=0, le=10, allow_inf_nan=False
    )
    motor_count: int = Field(ge=1, le=20)
    wheel_radius_m: float = Field(
        ge=0.005, le=0.5, allow_inf_nan=False
    )
    slope_degrees: float = Field(
        default=0, ge=-89, le=89, allow_inf_nan=False
    )

    # Optional component catalogue selection.
    motor_component_id: str | None = None

    # Optional installed component IDs from the builder.
    # None means the caller did not provide component configuration.
    installed_component_ids: list[str] | None = None

    # Motor and battery operating inputs.
    motor_rpm: float = Field(
        default=100, ge=0, le=10000, allow_inf_nan=False
    )
    battery_voltage_v: float = Field(
        default=12, ge=1, le=60, allow_inf_nan=False
    )

    # Motor datasheet parameters.
    motor_rated_voltage_v: float | None = Field(
        default=None, gt=0, le=60, allow_inf_nan=False
    )
    motor_no_load_rpm: float | None = Field(
        default=None, gt=0, le=10000, allow_inf_nan=False
    )
    motor_stall_torque_nm: float | None = Field(
        default=None, ge=0, le=10, allow_inf_nan=False
    )

    gear_ratio: float = Field(
        default=1, ge=1, le=100, allow_inf_nan=False
    )
    drivetrain_efficiency: float = Field(
        default=0.85, gt=0, le=1, allow_inf_nan=False
    )
    gearbox_efficiency: float = Field(
        default=1.0, gt=0, le=1, allow_inf_nan=False
    )
    traction_coefficient: float = Field(
        default=0.7, ge=0, le=2, allow_inf_nan=False
    )
    rolling_resistance_coefficient: float = Field(
        default=0.03, ge=0, le=1, allow_inf_nan=False
    )
    driven_weight_fraction: float = Field(
        default=1.0, ge=0, le=1, allow_inf_nan=False
    )

    @model_validator(mode="after")
    def validate_motor_specifications(self):
        supplied = (
            self.motor_rated_voltage_v is not None,
            self.motor_no_load_rpm is not None,
            self.motor_stall_torque_nm is not None,
        )

        if any(supplied) and not all(supplied):
            raise ValueError(
                "Provide motor_rated_voltage_v, motor_no_load_rpm, "
                "and motor_stall_torque_nm together."
            )

        if self.motor_component_id is not None and any(supplied):
            raise ValueError(
                "When motor_component_id is provided, motor datasheet "
                "values are loaded from the catalogue. Do not provide "
                "the same datasheet fields separately."
            )

        if self.installed_component_ids is not None:
            if not all(
                isinstance(component_id, str) and component_id.strip()
                for component_id in self.installed_component_ids
            ):
                raise ValueError(
                    "installed_component_ids must contain non-empty strings."
                )

        return self


class MotionSimulationRequest(SimulationRequest):
    total_mass_kg: float = Field(
        ge=0.01, le=100.0, allow_inf_nan=False
    )
    motor_torque_nm: float | None = Field(
        default=None, ge=0, le=10, allow_inf_nan=False
    )
    duration_s: float = Field(
        default=5.0, ge=0.0, le=3600.0, allow_inf_nan=False
    )
    time_step_s: float = Field(
        default=0.1, ge=0.001, le=10.0, allow_inf_nan=False
    )
    initial_velocity_ms: float = Field(
        default=0.0, ge=0.0, allow_inf_nan=False
    )
    initial_position_m: float = Field(
        default=0.0, ge=0.0, allow_inf_nan=False
    )

    @model_validator(mode="before")
    @classmethod
    def reject_booleans(cls, data):
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, bool):
                    raise ValueError(f"{k} cannot be a boolean.")
        return data

    @model_validator(mode="after")
    def validate_motor_selection(self):
        supplied_datasheet = (
            self.motor_rated_voltage_v is not None,
            self.motor_no_load_rpm is not None,
            self.motor_stall_torque_nm is not None,
        )
        if (
            self.motor_component_id is None
            and self.motor_torque_nm is None
            and not any(supplied_datasheet)
        ):
            raise ValueError(
                "Provide motor_torque_nm, motor_component_id, or motor datasheet specifications."
            )
        return self

    @model_validator(mode="after")
    def validate_trajectory_sample_limit(self):
        if self.time_step_s > 0:
            estimated_samples = int(math.ceil(self.duration_s / self.time_step_s)) + 1
            if estimated_samples > MAX_TRAJECTORY_SAMPLES:
                raise ValueError(
                    f"The combination of duration_s={self.duration_s} and time_step_s={self.time_step_s} "
                    f"would generate {estimated_samples} trajectory samples, exceeding the "
                    f"safety limit of {MAX_TRAJECTORY_SAMPLES}. Increase time_step_s or reduce duration_s."
                )
        return self


class TestRequestModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def reject_boolean_numbers(cls, data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, bool):
                    raise ValueError(f"{key} cannot be a boolean.")
        return data


class TestRobotConfiguration(TestRequestModel):
    total_mass_kg: float = Field(gt=0, le=100, allow_inf_nan=False)
    motor_torque_nm: float = Field(ge=0, le=10, allow_inf_nan=False)
    motor_count: int = Field(ge=1, le=20)
    wheel_radius_m: float = Field(ge=0.005, le=0.5, allow_inf_nan=False)
    wheel_count: int = Field(ge=1, le=32)
    motor_rpm: float = Field(default=100, ge=0, le=10000, allow_inf_nan=False)
    battery_voltage_v: float = Field(default=12, ge=1, le=60, allow_inf_nan=False)
    gear_ratio: float = Field(default=1, ge=1, le=100, allow_inf_nan=False)
    drivetrain_efficiency: float = Field(default=0.85, gt=0, le=1, allow_inf_nan=False)
    gearbox_efficiency: float = Field(default=1, gt=0, le=1, allow_inf_nan=False)
    driven_weight_fraction: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)
    gravity_m_s2: float = Field(default=9.81, gt=0, le=30, allow_inf_nan=False)
    spec_notes: list[str] = Field(default_factory=list, max_length=50)
    installed_component_ids: list[str] = Field(default_factory=list, max_length=100)


class TerrainTestRequest(TestRequestModel):
    robot: TestRobotConfiguration
    campaign_id: str | None = Field(default=None, max_length=100)
    terrain_type: Literal[
        "flat_concrete", "rough_concrete", "sand", "loose_soil", "gravel",
        "rocky_terrain", "mud", "lunar_regolith", "martian_terrain",
    ]
    slope_degrees: float = Field(default=0, ge=-89, le=89, allow_inf_nan=False)
    friction_coefficient: float | None = Field(default=None, ge=0, le=2, allow_inf_nan=False)
    rolling_resistance_coefficient: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    obstacle_type: Literal[
        "none", "small_rock", "large_rock", "ramp", "step", "trench",
        "crater", "uneven_ground", "slope", "narrow_pathway",
    ] = "none"
    obstacle_height_m: float = Field(default=0, ge=0, le=2, allow_inf_nan=False)
    obstacle_width_m: float = Field(default=0, ge=0, le=5, allow_inf_nan=False)
    duration_s: float = Field(default=10, gt=0, le=3600, allow_inf_nan=False)


class PayloadTestRequest(TestRequestModel):
    robot: TestRobotConfiguration
    campaign_id: str | None = Field(default=None, max_length=100)
    payload_mass_kg: float = Field(ge=0, le=50, allow_inf_nan=False)
    payload_position_x_m: float | None = Field(default=None, allow_inf_nan=False)
    payload_position_y_m: float | None = Field(default=None, allow_inf_nan=False)
    payload_position_z_m: float | None = Field(default=None, allow_inf_nan=False)
    payload_distribution: Literal["centered", "front", "rear", "left", "right", "custom"] = "centered"
    terrain_type: Literal[
        "flat_concrete", "rough_concrete", "sand", "loose_soil", "gravel",
        "rocky_terrain", "mud", "lunar_regolith", "martian_terrain",
    ] = "flat_concrete"
    slope_degrees: float = Field(default=0, ge=-89, le=89, allow_inf_nan=False)
    friction_coefficient: float | None = Field(default=None, ge=0, le=2, allow_inf_nan=False)
    rolling_resistance_coefficient: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    safety_margin_fraction: float = Field(default=0.2, ge=0, lt=1, allow_inf_nan=False)
    sweep_step_kg: float = Field(default=0.1, gt=0, le=5, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_total_mass(self):
        if self.robot.total_mass_kg + self.payload_mass_kg > 100:
            raise ValueError("The combined robot and payload mass cannot exceed 100 kg in this model.")
        return self


class StructuralTestRequest(TestRequestModel):
    test_type: Literal["compression", "tension", "bending", "wheel_pressure"]
    robot: TestRobotConfiguration | None = None
    material_name: str | None = Field(default=None, max_length=100)
    density_kg_m3: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    yield_strength_pa: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    ultimate_strength_pa: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    load_force_n: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    cross_section_area_m2: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    member_length_m: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    youngs_modulus_pa: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    allowable_strength_pa: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    span_m: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    width_m: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    thickness_m: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    support_condition: Literal["simply_supported_center_load", "unsupported"] = "unsupported"
    normal_force_n: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    contact_area_m2: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    allowable_contact_pressure_pa: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class EnvironmentTestRequest(TestRequestModel):
    robot: TestRobotConfiguration | None = None
    scenario: Literal[
        "cold", "normal", "hot", "temperature_cycling", "dust", "sand",
        "low_vibration", "medium_vibration", "high_vibration",
        "small_impact", "medium_impact", "high_impact", "drop",
        "reduced_pressure", "vacuum",
    ]
    duration_s: float = Field(default=60, gt=0, le=86400, allow_inf_nan=False)
    temperature_c: float | None = Field(default=None, ge=-273.15, le=1000, allow_inf_nan=False)
    vibration_acceleration_ms2: float | None = Field(default=None, ge=0, le=10000, allow_inf_nan=False)
    impact_energy_j: float | None = Field(default=None, ge=0, le=1e7, allow_inf_nan=False)
    pressure_pa: float | None = Field(default=None, ge=0, le=1e8, allow_inf_nan=False)


class EnduranceTestRequest(TestRequestModel):
    robot: TestRobotConfiguration | None = None
    duration_s: float = Field(gt=0, le=86400, allow_inf_nan=False)
    voltage_v: float = Field(gt=0, le=60, allow_inf_nan=False)
    current_a: float | None = Field(default=None, ge=0, le=1000, allow_inf_nan=False)
    battery_capacity_ah: float | None = Field(default=None, gt=0, le=10000, allow_inf_nan=False)
    speed_ms: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)


class AssemblyValidationRequest(BaseModel):
    component_ids: list[str] = Field(default_factory=list, max_length=100)
    reject_unknown: bool = True


# ------------------------------------------
# 6. Robot Testing Lab API
# ------------------------------------------

@app.get("/api/tests/campaigns")
def list_test_campaigns():
    return {"campaigns": test_campaigns()}


@app.post("/api/assembly/validate")
def validate_assembly(request: AssemblyValidationRequest):
    catalogue = {component["id"]: component for component in get_components()}
    ids = request.component_ids
    unknown = [component_id for component_id in ids if component_id not in catalogue]
    if unknown and request.reject_unknown:
        return {
            "status": "FAIL",
            "valid": False,
            "errors": [
                f"Unknown component ID: {component_id}"
                for component_id in unknown
            ],
            "warnings": [],
            "summary": "Remove unknown components before validation.",
        }

    installed = [catalogue[component_id] for component_id in ids if component_id in catalogue]
    counts = {
        "chassis": sum(component["category"] == "structure" and "chassis" in component["id"] for component in installed),
        "motor": sum(component["category"] == "actuator" for component in installed),
        "wheel": sum(component["category"] == "mechanical" and "wheel" in component["id"] for component in installed),
        "battery": sum(component["category"] == "power" for component in installed),
        "controller": sum(component["category"] == "electrical" and "controller" in component["id"] for component in installed),
        "sensor": sum(component["category"] == "sensor" for component in installed),
    }
    # Modular WALL-E assemblies are validated through their module IDs.
    counts["walle_head"] = sum(component["id"] == "walle_head" for component in installed)
    counts["walle_body"] = sum(component["id"] == "walle_body" for component in installed)
    counts["walle_tracks"] = sum(component["id"] == "walle_tracks" for component in installed)
    counts["chassis"] += counts["walle_body"]
    counts["motor"] += counts["walle_tracks"]
    counts["wheel"] += counts["walle_tracks"]
    counts["battery"] += counts["walle_body"]

    errors = []
    warnings = []
    if counts["chassis"] == 0:
        errors.append("A chassis or structural frame is required.")
    if counts["motor"] == 0:
        errors.append("At least one motor is required for a mobile robot.")
    if counts["wheel"] == 0:
        errors.append("At least one wheel is required for a wheeled robot.")
    if counts["battery"] == 0:
        warnings.append("No power source is installed. Electrical operation cannot be evaluated.")
    if counts["motor"] > counts["wheel"]:
        warnings.append("There are more motors than wheels. Verify that each motor drives a wheel.")
    if counts["wheel"] > counts["motor"]:
        warnings.append("There are wheels without an identified drivetrain motor.")
    if counts["sensor"] and counts["controller"] == 0:
        warnings.append("Sensors are installed without an identified controller.")
    if counts["motor"] and counts["battery"] == 0:
        warnings.append("Motors are installed without a battery connection.")

    status = "FAIL" if errors or unknown else ("WARNING" if warnings else "PASS")
    return {
        "status": status,
        "valid": not errors and not unknown,
        "errors": errors,
        "warnings": warnings,
        "counts": counts,
        "summary": "Assembly is ready for testing." if status == "PASS"
            else "Assembly requires attention before testing." if status == "WARNING"
            else "Assembly validation found blocking errors.",
    }


@app.post("/api/tests/terrain")
def test_terrain(request: TerrainTestRequest):
    try:
        return run_terrain_test(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@app.post("/api/tests/payload")
def test_payload(request: PayloadTestRequest):
    try:
        return run_payload_test(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@app.post("/api/tests/structural")
def test_structure(request: StructuralTestRequest):
    try:
        return run_structural_test(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@app.post("/api/tests/environment")
def test_environment(request: EnvironmentTestRequest):
    return run_environment_test(request)


@app.post("/api/tests/endurance")
def test_endurance(request: EnduranceTestRequest):
    return run_endurance_test(request)


# ------------------------------------------
# 4. Run simulation
# ------------------------------------------

@app.post("/api/simulate")
def run_simulation(request: SimulationRequest):
    inputs = request.model_dump()

    component_id = inputs.pop("motor_component_id", None)
    installed_component_ids = inputs.pop(
        "installed_component_ids", None
    )

    component = None

    if component_id is not None:
        component = find_motor_component(component_id)

        inputs["motor_torque_nm"] = component["max_torque_nm"]
        inputs["motor_rated_voltage_v"] = component["rated_voltage_v"]
        inputs["motor_no_load_rpm"] = component["no_load_rpm"]
        inputs["motor_stall_torque_nm"] = component["stall_torque_nm"]

        if component.get("gear_ratio") is not None:
            inputs["gear_ratio"] = component["gear_ratio"]

    try:
        result = simulate_robot(**inputs)

        analysis = analyze_simulation(
            result,
            installed_component_ids=installed_component_ids,
        )

        response = {
            "status": "success",
            "simulation": result,
            "engineering_analysis": analysis,
        }

        if component is not None:
            response["selected_motor"] = {
                "id": component["id"],
                "name": component["name"],
                "spec_status": component["spec_status"],
                "source": "component_catalogue",
            }

        return response

    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


# ------------------------------------------
# 5. Run motion simulation
# ------------------------------------------

@app.post("/api/simulate-motion")
def run_motion_simulation(request: MotionSimulationRequest):
    inputs = request.model_dump()

    component_id = inputs.pop("motor_component_id", None)
    installed_component_ids = inputs.pop(
        "installed_component_ids", None
    )

    component = None

    if component_id is not None:
        try:
            component = find_motor_component(component_id)
        except HTTPException as error:
            raise HTTPException(status_code=422, detail=error.detail)

        inputs["motor_torque_nm"] = component["max_torque_nm"]
        inputs["motor_rated_voltage_v"] = component["rated_voltage_v"]
        inputs["motor_no_load_rpm"] = component["no_load_rpm"]
        inputs["motor_stall_torque_nm"] = component["stall_torque_nm"]

        if component.get("gear_ratio") is not None:
            inputs["gear_ratio"] = component["gear_ratio"]

    try:
        if inputs.get("motor_torque_nm") is None:
            if inputs.get("motor_stall_torque_nm") is not None:
                inputs["motor_torque_nm"] = inputs["motor_stall_torque_nm"]
            else:
                inputs["motor_torque_nm"] = 0.0

        result = simulate_robot_motion(**inputs)

        # Run engineering analysis when base simulation is available
        analysis = analyze_simulation(
            result.get("base_simulation") or result,
            installed_component_ids=installed_component_ids,
        )

        response = {
            "status": "success",
            "engineering_analysis": analysis,
            **result,
        }

        if component is not None:
            response["selected_motor"] = {
                "id": component["id"],
                "name": component["name"],
                "spec_status": component["spec_status"],
                "source": "component_catalogue",
            }

        return response

    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


# ------------------------------------------
# 7. Frontend
# ------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount(
    "/ui",
    StaticFiles(directory=str(FRONTEND_DIR), html=True),
    name="frontend",
)