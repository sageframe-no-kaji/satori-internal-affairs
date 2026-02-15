"""Vitals computation using worst-wins algorithm.

Computes current patient vitals from baseline, active node vitals,
and timer stage vitals. Takes the most dangerous value for each vital sign.
"""

from satori.game_state import GameState
from satori.models.case_definition import Node, VitalSigns


class VitalsComputer:
    """Computes current vitals from active nodes using worst-wins algorithm."""

    # Normal ranges for determining "worst"
    NORMAL_RANGES = {
        "heart_rate": (60, 100),
        "blood_pressure_systolic": (90, 140),
        "blood_pressure_diastolic": (60, 90),
        "temperature": (97.0, 99.5),
        "respiratory_rate": (12, 20),
        "o2_saturation": (95, 100),
    }

    def compute_vitals(self, baseline: VitalSigns, active_nodes: list[Node], state: GameState) -> VitalSigns:
        """Compute current vitals using worst-wins algorithm.

        Sources of vitals (in addition to baseline):
        1. node.vital_signs — base vitals for each active node
        2. Timer stage vitals — from the highest reached stage of each
           active node's timer (state.timer_stages tracks this)

        For each vital field:
        1. Start with baseline value
        2. Collect values from all active nodes' vital_signs
        3. Collect values from current timer stage vital_signs
           (looked up via state.timer_stages[node_id])
        4. Take the "worst" (most dangerous) value

        "Worst" means furthest from normal range:
        - heart_rate: furthest from 60-100
        - blood_pressure_systolic: highest (hypertensive crisis is acute risk)
        - blood_pressure_diastolic: highest
        - temperature: furthest from 97.0-99.5
        - respiratory_rate: furthest from 12-20
        - o2_saturation: lowest (desaturation is acute risk)

        Args:
            baseline: Patient's baseline vital signs
            active_nodes: List of currently active nodes
            state: Current game state (for timer_stages tracking)

        Returns:
            Computed VitalSigns with worst values
        """
        # Collect all values for each vital
        hr_values = self._collect_vital_values("heart_rate", baseline, active_nodes, state)
        bp_sys_values = self._collect_vital_values("blood_pressure_systolic", baseline, active_nodes, state)
        bp_dia_values = self._collect_vital_values("blood_pressure_diastolic", baseline, active_nodes, state)
        temp_values = self._collect_vital_values("temperature", baseline, active_nodes, state)
        rr_values = self._collect_vital_values("respiratory_rate", baseline, active_nodes, state)
        o2_values = self._collect_vital_values("o2_saturation", baseline, active_nodes, state)

        # Take worst for each
        return VitalSigns(
            heart_rate=self._worst_value("heart_rate", hr_values),
            blood_pressure_systolic=self._worst_value("blood_pressure_systolic", bp_sys_values),
            blood_pressure_diastolic=self._worst_value("blood_pressure_diastolic", bp_dia_values),
            temperature=self._worst_value("temperature", temp_values),
            respiratory_rate=self._worst_value("respiratory_rate", rr_values),
            o2_saturation=self._worst_value("o2_saturation", o2_values),
        )

    def _collect_vital_values(
        self,
        vital_name: str,
        baseline: VitalSigns,
        active_nodes: list[Node],
        state: GameState,
    ) -> list[float]:
        """Collect all candidate values for a vital.

        From baseline, active node vitals, and current timer stage vitals.

        Args:
            vital_name: Name of the vital field
            baseline: Baseline vital signs
            active_nodes: List of active nodes
            state: Current game state

        Returns:
            List of all candidate values for this vital
        """
        values: list[float] = []
        baseline_val = getattr(baseline, vital_name, None)
        if baseline_val is not None:
            values.append(float(baseline_val))

        for node in active_nodes:
            # Node-level vitals
            if node.vital_signs:
                val = getattr(node.vital_signs, vital_name, None)
                if val is not None:
                    values.append(float(val))

            # Timer-stage vitals (if node has a timer and has reached stages)
            if node.timer and node.timer.stages and node.id in state.timer_stages:
                current_stage_idx = state.timer_stages[node.id]
                # Collect vitals from all stages that have been reached
                # (stages are indexed by at_minutes, we store highest reached index)
                for stage in node.timer.stages:
                    # Check if this stage has been reached
                    if stage.at_minutes <= current_stage_idx and stage.vital_signs:
                        val = getattr(stage.vital_signs, vital_name, None)
                        if val is not None:
                            values.append(float(val))

        return values

    def _worst_value(self, vital_name: str, values: list[float]) -> int | float | None:
        """Determine worst value for a specific vital.

        Strategy per vital:
        - o2_saturation: lowest wins (desaturation)
        - blood_pressure_systolic, blood_pressure_diastolic: highest wins
        - heart_rate, respiratory_rate, temperature: furthest from normal midpoint

        Args:
            vital_name: Name of the vital
            values: List of candidate values

        Returns:
            The worst value, or None if no values
        """
        if not values:
            return None

        # Integer vitals should return int, float vitals return float
        is_int_vital = vital_name in {
            "heart_rate",
            "blood_pressure_systolic",
            "blood_pressure_diastolic",
            "respiratory_rate",
            "o2_saturation",
        }

        match vital_name:
            case "o2_saturation":
                # Lowest is worst
                worst = min(values)
            case "blood_pressure_systolic" | "blood_pressure_diastolic":
                # Highest is worst (hypertensive crisis)
                worst = max(values)
            case "heart_rate" | "respiratory_rate" | "temperature":
                # Furthest from normal midpoint is worst
                normal_range = self.NORMAL_RANGES.get(vital_name)
                if normal_range:
                    midpoint = (normal_range[0] + normal_range[1]) / 2
                    # Find value with maximum distance from midpoint
                    worst = max(values, key=lambda v: abs(v - midpoint))
                else:
                    # Fallback if no range defined
                    worst = max(values)
            case _:
                # Unknown vital - fallback to max
                worst = max(values)

        # Convert to appropriate type
        return int(worst) if is_int_vital else worst
