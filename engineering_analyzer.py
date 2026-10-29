# ==========================================
# BLUEPRINT - Engineering Analyzer
# ==========================================

def analyze_simulation(
    simulation: dict,
    installed_component_ids: list[str] | None = None,
) -> dict:
    """
    Analyze simulation results and return engineering checks.

    This is a simplified rule-based analysis, not real-world validation.
    """

    # Read simulation results.
    net_force = float(simulation["net_force_n"])
    acceleration = float(
        simulation["theoretical_acceleration_ms2"]
    )

    driving_force = float(
        simulation.get("driving_force_n", 0.0)
    )
    gravity_resistance = float(
        simulation.get("gravity_resistance_n", 0.0)
    )
    rolling_resistance = float(
        simulation.get("rolling_resistance_n", 0.0)
    )

    traction_limited = bool(
        simulation.get("traction_limited", False)
    )

    can_move = bool(
        simulation.get("can_move_under_model", net_force > 0)
    )

    modeled_resistance = (
        gravity_resistance + rolling_resistance
    )

    checks = []
    warnings = []
    suggestions = []

    # --------------------------------------
    # 1. Battery presence validation
    # --------------------------------------

    # Only validate battery presence when the caller provides
    # an explicit installed-component list.
    if installed_component_ids is not None:
        has_battery = (
            "battery_basic" in installed_component_ids
        )

        if has_battery:
            checks.append({
                "name": "battery_presence",
                "status": "pass",
                "message": "A battery component is installed.",
            })
        else:
            checks.append({
                "name": "battery_presence",
                "status": "review",
                "message": "No battery component was found.",
            })

            warnings.append(
                "Battery component is missing from the robot configuration."
            )

            suggestions.append(
                "Add a battery component before evaluating the robot's power system."
            )

    # --------------------------------------
    # 2. Movement validation
    # --------------------------------------

    if can_move:
        checks.append({
            "name": "movement",
            "status": "pass",
            "message": "The model predicts positive net force.",
        })
    else:
        checks.append({
            "name": "movement",
            "status": "fail",
            "message": "The model predicts that the robot may not move.",
        })

        warnings.append(
            "The robot may not move because modeled resistance "
            "meets or exceeds the available driving force."
        )

        suggestions.append(
            "Increase available motor torque or reduce the slope, "
            "mass, or rolling resistance, then run the simulation again."
        )

    # --------------------------------------
    # 3. Traction validation
    # --------------------------------------

    if traction_limited:
        checks.append({
            "name": "traction",
            "status": "review",
            "message": (
                "Driving force is limited by the traction model."
            ),
        })

        warnings.append(
            "Available traction limits the driving force in this model."
        )

        suggestions.append(
            "Check wheel grip, driven-wheel loading, and the assumed "
            "traction coefficient."
        )
    else:
        checks.append({
            "name": "traction",
            "status": "pass",
            "message": "The model is not traction-limited.",
        })

    # --------------------------------------
    # 4. Acceleration validation
    # --------------------------------------

    # Exactly 5.0 m/s² does not trigger the warning.
    if acceleration > 5.0:
        checks.append({
            "name": "acceleration",
            "status": "review",
            "message": (
                "Theoretical acceleration exceeds 5.0 m/s²."
            ),
        })

        warnings.append(
            "Theoretical acceleration is high; check motor torque, "
            "traction, stability, and the intended operating conditions."
        )

        suggestions.append(
            "Validate the acceleration against the robot's stability, "
            "motor limits, and real-world test results."
        )
    else:
        checks.append({
            "name": "acceleration",
            "status": "pass",
            "message": (
                "Theoretical acceleration is within the review threshold."
            ),
        })

    # --------------------------------------
    # 5. Model limitations
    # --------------------------------------

    warnings.append(
        "Results are theoretical estimates based on simplified physics "
        "and the supplied component parameters."
    )

    # Remove duplicate suggestions while preserving their order.
    suggestions = list(dict.fromkeys(suggestions))

    # --------------------------------------
    # 6. Overall analysis status
    # --------------------------------------

    requires_review = any(
        check["status"] in ("fail", "review")
        for check in checks
    )

    analysis_status = (
        "review_required" if requires_review else "passed"
    )

    # --------------------------------------
    # 7. Analysis response
    # --------------------------------------

    return {
        "analysis_status": analysis_status,
        "checks": checks,
        "warnings": warnings,
        "suggestions": suggestions,
        "modeled_resistance_n": round(
            modeled_resistance, 3
        ),
        "model_type": "simplified_robot_force_analysis",
    }