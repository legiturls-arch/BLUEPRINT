# ==========================================
# BLUEPRINT - Virtual Engineering Lab API
# ==========================================

import math
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from components import get_components
from physics_engine import (
    simulate_robot,
    simulate_robot_motion,
    MAX_TRAJECTORY_SAMPLES,
)
from engineering_analyzer import analyze_simulation


app = FastAPI(
    title="BLUEPRINT - Virtual Engineering Lab",
    description="AI-assisted engineering simulation platform",
    version="0.4.0",
)


# ------------------------------------------
# 1. Basic routes
# ------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Welcome to BLUEPRINT Virtual Engineering Lab",
        "status": "running",
    }


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
        default=0, ge=0, le=89, allow_inf_nan=False
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
        raise HTTPException(status_code=400, detail=str(error))


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
# 6. Frontend
# ------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount(
    "/ui",
    StaticFiles(directory=str(FRONTEND_DIR), html=True),
    name="frontend",
)