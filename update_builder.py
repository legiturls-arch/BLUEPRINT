import sys

path = r"D:\BLUEPRINT\frontend\builder.js"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Normalize CRLF for matching
has_crlf = "\r\n" in content
clean_content = content.replace("\r\n", "\n")

old_sim_end = """    setSimStatus(
      "complete",
      [
        `Time-based motion simulation complete (${data.duration_s}s, ${data.trajectory ? data.trajectory.length : 0} samples).`,
        ...notes
      ].join(" "),
      elapsed
    );
  } catch (error) {"""

new_sim_end = """    setSimStatus(
      "complete",
      [
        `Time-based motion simulation complete (${data.duration_s}s, ${data.trajectory ? data.trajectory.length : 0} samples).`,
        ...notes
      ].join(" "),
      elapsed
    );

    // Start 3D physical trajectory playback
    if (data.can_move && Array.isArray(data.trajectory) && data.trajectory.length > 0 && data.distance_traveled_m > 0) {
      startTrajectoryPlayback(data, notes, elapsed);
    } else {
      stopTrajectoryPlayback(true);
      if (!data.can_move || data.distance_traveled_m <= 0) {
        setText(
          "drive-status",
          "Robot stationary: zero displacement modeled (insufficient net force)."
        );
      } else if (!Array.isArray(data.trajectory) || data.trajectory.length === 0) {
        setText(
          "drive-status",
          "Playback unavailable: trajectory data is missing or empty."
        );
        showError("Trajectory playback could not start: invalid trajectory data.");
      }
    }
  } catch (error) {"""

assert old_sim_end in clean_content, "old_sim_end not found!"
clean_content = clean_content.replace(old_sim_end, new_sim_end, 1)

old_driving_section = """// --------------------------------------------------
// SIMPLIFIED ROBOT DRIVING
// This moves every part together by a fixed visual speed. It is not a
// physics simulation and has no collision detection.
// --------------------------------------------------

function stopRobot() {
  if (driveTimer) {
    clearInterval(driveTimer);
    driveTimer = null;
  }

  currentDriveDirection = null;
}

function driveRobot(direction) {
  const chassis = parts.find(
    part => part.componentId === "chassis_basic"
  );

  if (
    !chassis ||
    countParts(isMotorPart) === 0 ||
    countParts(isWheelPart) < 2
  ) {
    setText(
      "drive-status",
      "Add a chassis, at least one motor and two wheels."
    );
    return;
  }

  if (direction === "stop") {
    stopRobot();
    setText("drive-status", "Robot stopped");
    return;
  }

  if (
    simulatedAcceleration === null ||
    !Number.isFinite(simulatedAcceleration)
  ) {
    setText("drive-status", "Run the simulation first.");
    return;
  }

  if (simulatedAcceleration <= 0) {
    setText(
      "drive-status",
      "Insufficient modeled acceleration. Check simulation results."
    );
    return;
  }

  const movement = {
    forward: [0, -1],
    backward: [0, 1],
    left: [-1, 0],
    right: [1, 0]
  };

  const vector = movement[direction];
  if (!vector) return;

  if (driveTimer && currentDriveDirection === direction) return;

  stopRobot();
  currentDriveDirection = direction;

  const dt = 0.03;
  const maxSpeed = 2;
  let velocity = 0;

  const visualAcceleration = Math.min(simulatedAcceleration, 0.3);

  driveTimer = setInterval(() => {
    velocity = Math.min(velocity + visualAcceleration * dt, maxSpeed);
    const distance = velocity * dt;

    parts.forEach(part => {
      part.group.position.x += vector[0] * distance;
      part.group.position.z += vector[1] * distance;
    });

    // Keep the inspector in step with the moving part.
    if (selected) writeInspector();
  }, dt * 1000);

  setText(
    "drive-status",
    "Driving: " + direction + " | Visual steering (scaled acceleration, not physical trajectory)"
  );
}"""

new_driving_section = """// --------------------------------------------------
// TIME-BASED TRAJECTORY PLAYBACK
// Animates the assembled robot according to physical trajectory coordinates.
// --------------------------------------------------

function interpolateTrajectory(samples, time) {
  if (!samples || samples.length === 0) {
    return { position_m: 0, velocity_ms: 0, acceleration_ms2: 0, time_s: time };
  }
  if (time <= samples[0].time_s) {
    return samples[0];
  }
  const last = samples[samples.length - 1];
  if (time >= last.time_s) {
    return last;
  }

  let low = 0;
  let high = samples.length - 1;
  while (low <= high) {
    const mid = (low + high) >> 1;
    if (samples[mid].time_s <= time) {
      low = mid + 1;
    } else {
      high = mid - 1;
    }
  }

  const idx = Math.max(0, high);
  const s0 = samples[idx];
  const s1 = samples[Math.min(idx + 1, samples.length - 1)];
  const dt = s1.time_s - s0.time_s;
  if (dt <= 1e-6) return s0;

  const alpha = (time - s0.time_s) / dt;
  return {
    time_s: time,
    position_m: s0.position_m + alpha * (s1.position_m - s0.position_m),
    velocity_ms: s0.velocity_ms + alpha * (s1.velocity_ms - s0.velocity_ms),
    acceleration_ms2: s0.acceleration_ms2 + alpha * (s1.acceleration_ms2 - s0.acceleration_ms2)
  };
}

function stopTrajectoryPlayback(resetToOrigin = false) {
  if (trajectoryPlayback) {
    if (trajectoryPlayback.animId) {
      cancelAnimationFrame(trajectoryPlayback.animId);
      trajectoryPlayback.animId = null;
    }
    trajectoryPlayback.active = false;
  }

  if (resetToOrigin) {
    for (const part of parts) {
      if (part.basePosition && part.group) {
        part.group.position.set(
          part.basePosition.x,
          part.basePosition.y,
          part.basePosition.z
        );
      }
    }
    if (selected) writeInspector();
    render();
  }
}

function startTrajectoryPlayback(data, notes = [], elapsedApiMs = null) {
  stopRobot();
  stopTrajectoryPlayback(true);

  if (!data || !Array.isArray(data.trajectory) || data.trajectory.length === 0) {
    setText(
      "drive-status",
      "Playback unavailable: trajectory data is missing or empty."
    );
    showError("Trajectory playback could not start: invalid trajectory data.");
    return;
  }

  // Ensure all parts have a recorded basePosition before animating
  for (const part of parts) {
    if (!part.basePosition && part.group) {
      part.basePosition = {
        x: part.group.position.x,
        y: part.group.position.y,
        z: part.group.position.z
      };
    }
    if (part.basePosition && part.group) {
      part.group.position.set(
        part.basePosition.x,
        part.basePosition.y,
        part.basePosition.z
      );
    }
  }
  if (selected) writeInspector();
  render();

  const trajectory = data.trajectory;
  const duration = Number(data.duration_s) || trajectory[trajectory.length - 1].time_s || 5.0;
  const totalDisp = Number(data.distance_traveled_m) || 0;

  if (totalDisp <= 0 || !data.can_move) {
    setText(
      "drive-status",
      "Robot stationary: zero displacement modeled (insufficient net force)."
    );
    return;
  }

  const slopeDeg = Number(data.slope_degrees ?? simulatedSlopeDegrees ?? 0);
  const slopeRad = (slopeDeg * Math.PI) / 180;
  const cosSlope = Math.cos(slopeRad);
  const sinSlope = Math.sin(slopeRad);
  const initialPos = Number(data.initial_position_m) || trajectory[0].position_m || 0;

  const currentVersion = simulationVersion;
  const startTime = performance.now();

  trajectoryPlayback = {
    active: true,
    completed: false,
    animId: null,
    data: data,
    duration: duration,
    cosSlope: cosSlope,
    sinSlope: sinSlope,
    initialPos: initialPos
  };

  setText(
    "drive-status",
    `Starting trajectory playback: 0.00s / ${duration.toFixed(2)}s (target: ${totalDisp.toFixed(2)}m)`
  );

  function step() {
    if (currentVersion !== simulationVersion) return;
    if (!trajectoryPlayback || !trajectoryPlayback.active) return;

    const now = performance.now();
    const elapsedSec = (now - startTime) / 1000;
    const simTime = Math.min(elapsedSec, duration);

    const state = interpolateTrajectory(trajectory, simTime);
    const disp = state.position_m - initialPos;

    const deltaZ = -disp * cosSlope;
    const deltaY = disp * sinSlope;

    for (const part of parts) {
      if (part.basePosition && part.group) {
        part.group.position.x = part.basePosition.x;
        part.group.position.y = part.basePosition.y + deltaY;
        part.group.position.z = part.basePosition.z + deltaZ;
      }
    }

    if (selected) writeInspector();
    render();

    setText(
      "drive-status",
      `Playing trajectory: t=${simTime.toFixed(2)}s / ${duration.toFixed(2)}s | disp=${disp.toFixed(2)}m | v=${state.velocity_ms.toFixed(2)}m/s | a=${state.acceleration_ms2.toFixed(2)}m/s²`
    );

    if (elapsedSec < duration) {
      trajectoryPlayback.animId = requestAnimationFrame(step);
    } else {
      trajectoryPlayback.active = false;
      trajectoryPlayback.completed = true;
      trajectoryPlayback.animId = null;

      setText(
        "drive-status",
        `Trajectory playback completed: traveled ${disp.toFixed(2)}m in ${duration.toFixed(2)}s (final v: ${state.velocity_ms.toFixed(2)}m/s).`
      );
      setSimStatus(
        "complete",
        [
          `Trajectory playback complete (${duration.toFixed(1)}s, ${trajectory.length} samples, ${disp.toFixed(2)}m traveled).`,
          ...notes
        ].join(" "),
        elapsedApiMs
      );
    }
  }

  trajectoryPlayback.animId = requestAnimationFrame(step);
}

// --------------------------------------------------
// MANUAL ROBOT DRIVING
// Visual steering with scaled acceleration for interactive exploration.
// --------------------------------------------------

function stopRobot() {
  if (driveTimer) {
    clearInterval(driveTimer);
    driveTimer = null;
  }

  currentDriveDirection = null;
}

function driveRobot(direction) {
  const chassis = parts.find(
    part => part.componentId === "chassis_basic"
  );

  if (
    !chassis ||
    countParts(isMotorPart) === 0 ||
    countParts(isWheelPart) < 2
  ) {
    setText(
      "drive-status",
      "Add a chassis, at least one motor and two wheels."
    );
    return;
  }

  if (direction === "stop") {
    if (trajectoryPlayback && trajectoryPlayback.active) {
      stopTrajectoryPlayback(false);
      setText(
        "drive-status",
        "Trajectory playback paused. Click Stop again to reset to origin."
      );
      return;
    } else if (trajectoryPlayback && !trajectoryPlayback.active) {
      stopTrajectoryPlayback(true);
      trajectoryPlayback = null;
      stopRobot();
      setText("drive-status", "Robot stopped and reset to assembly origin.");
      return;
    }

    stopRobot();
    setText("drive-status", "Robot stopped");
    return;
  }

  // If manual driving starts while trajectory playback is active, halt trajectory playback
  if (trajectoryPlayback && trajectoryPlayback.active) {
    stopTrajectoryPlayback(false);
  }

  for (const part of parts) {
    if (part.group) {
      part.basePosition = {
        x: part.group.position.x,
        y: part.group.position.y,
        z: part.group.position.z
      };
    }
  }

  if (
    simulatedAcceleration === null ||
    !Number.isFinite(simulatedAcceleration)
  ) {
    setText("drive-status", "Run the simulation first.");
    return;
  }

  if (simulatedAcceleration <= 0) {
    setText(
      "drive-status",
      "Insufficient modeled acceleration. Check simulation results."
    );
    return;
  }

  const movement = {
    forward: [0, -1],
    backward: [0, 1],
    left: [-1, 0],
    right: [1, 0]
  };

  const vector = movement[direction];
  if (!vector) return;

  if (driveTimer && currentDriveDirection === direction) return;

  stopRobot();
  currentDriveDirection = direction;

  const dt = 0.03;
  const maxSpeed = 2;
  let velocity = 0;

  const visualAcceleration = Math.min(simulatedAcceleration, 0.3);

  driveTimer = setInterval(() => {
    velocity = Math.min(velocity + visualAcceleration * dt, maxSpeed);
    const distance = velocity * dt;

    parts.forEach(part => {
      part.group.position.x += vector[0] * distance;
      part.group.position.z += vector[1] * distance;
      part.basePosition = {
        x: part.group.position.x,
        y: part.group.position.y,
        z: part.group.position.z
      };
    });

    // Keep the inspector in step with the moving part.
    if (selected) writeInspector();
  }, dt * 1000);

  setText(
    "drive-status",
    "Driving: " + direction + " | Visual steering (scaled acceleration, not physical trajectory)"
  );
}"""

assert old_driving_section in clean_content, "old_driving_section not found!"
clean_content = clean_content.replace(old_driving_section, new_driving_section, 1)

final_content = clean_content.replace("\n", "\r\n") if has_crlf else clean_content
with open(path, "w", encoding="utf-8") as f:
    f.write(final_content)

print("SUCCESS: builder.js updated cleanly.")

