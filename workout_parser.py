"""
Parser for plain text workout plans.
Converts human-readable workout descriptions to structured format.
"""

import re
from typing import List, Dict, Any, Optional, Tuple

from exercise_mapper import ExerciseMapper


class WorkoutParser:
    """Parse plain text workout descriptions into structured format."""

    def __init__(self):
        self.mapper = ExerciseMapper()

        # Patterns for parsing exercise lines
        self.patterns = {
            # "4x8 Pull-ups" or "4×8 Pull-ups"
            "sets_reps_name": re.compile(
                r'^(\d+)\s*[x×]\s*(\d+)[-–]?(\d+)?\s+(.+)$',
                re.IGNORECASE
            ),
            # "Pull-ups 4x8" or "Pull-ups - 4x8"
            "name_sets_reps": re.compile(
                r'^(.+?)[-–\s]+(\d+)\s*[x×]\s*(\d+)[-–]?(\d+)?$',
                re.IGNORECASE
            ),
            # "Pull-ups — 4 sets × 8 reps"
            "verbose": re.compile(
                r'^(.+?)[-–—:]+\s*(\d+)\s*sets?\s*[x×,]\s*(\d+)[-–]?(\d+)?\s*reps?',
                re.IGNORECASE
            ),
            # "3 sets of Push-ups"
            "sets_of_name": re.compile(
                r'^(\d+)\s*sets?\s*(?:of\s+)?(.+)$',
                re.IGNORECASE
            ),
            # Duration based: "Dead hang — 30 sec" or "Plank - 60s"
            "duration": re.compile(
                r'^(.+?)[-–—:\s]+(\d+)\s*(?:sec(?:onds?)?|s)$',
                re.IGNORECASE
            ),
            # "2×30 sec Dead hang"
            "sets_duration_name": re.compile(
                r'^(\d+)\s*[x×]\s*(\d+)\s*(?:sec(?:onds?)?|s)\s+(.+)$',
                re.IGNORECASE
            ),
        }

    def parse_exercise_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single exercise line.

        Args:
            line: Exercise description (e.g., "4x8 Bench Press")

        Returns:
            Exercise dict or None if unparseable
        """
        line = line.strip()

        # Skip empty lines, comments, headers
        if not line or line.startswith('#') or line.startswith('//'):
            return None

        # Skip common non-exercise lines
        skip_patterns = [
            r'^warm[\s-]?up',
            r'^cool[\s-]?down',
            r'^stretch',
            r'^rest',
            r'^\d+\s*min',
            r'^—+$',
            r'^-+$',
        ]
        for pattern in skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return None

        # Try each pattern
        result = None

        # Pattern: "4x8 Pull-ups"
        match = self.patterns["sets_reps_name"].match(line)
        if match:
            sets, reps_low, reps_high, name = match.groups()
            result = {
                "raw_name": name.strip(),
                "sets": int(sets),
                "reps": int(reps_low),
                "reps_high": int(reps_high) if reps_high else None,
                "type": "reps"
            }

        # Pattern: "Pull-ups 4x8"
        if not result:
            match = self.patterns["name_sets_reps"].match(line)
            if match:
                name, sets, reps_low, reps_high = match.groups()
                result = {
                    "raw_name": name.strip(),
                    "sets": int(sets),
                    "reps": int(reps_low),
                    "reps_high": int(reps_high) if reps_high else None,
                    "type": "reps"
                }

        # Pattern: "Pull-ups — 4 sets × 8 reps"
        if not result:
            match = self.patterns["verbose"].match(line)
            if match:
                name, sets, reps_low, reps_high = match.groups()
                result = {
                    "raw_name": name.strip(),
                    "sets": int(sets),
                    "reps": int(reps_low),
                    "reps_high": int(reps_high) if reps_high else None,
                    "type": "reps"
                }

        # Pattern: "2×30 sec Dead hang"
        if not result:
            match = self.patterns["sets_duration_name"].match(line)
            if match:
                sets, duration, name = match.groups()
                result = {
                    "raw_name": name.strip(),
                    "sets": int(sets),
                    "duration_seconds": int(duration),
                    "type": "duration"
                }

        # Pattern: "Dead hang — 30 sec"
        if not result:
            match = self.patterns["duration"].match(line)
            if match:
                name, duration = match.groups()
                result = {
                    "raw_name": name.strip(),
                    "sets": 1,
                    "duration_seconds": int(duration),
                    "type": "duration"
                }

        # Pattern: "3 sets of Push-ups"
        if not result:
            match = self.patterns["sets_of_name"].match(line)
            if match:
                sets, name = match.groups()
                result = {
                    "raw_name": name.strip(),
                    "sets": int(sets),
                    "reps": 10,  # Default reps
                    "type": "reps"
                }

        # If still no match, try to extract just the name
        if not result:
            # Check if it looks like an exercise name (not a section header)
            if len(line) > 3 and not line.endswith(':'):
                result = {
                    "raw_name": line,
                    "sets": 3,  # Default
                    "reps": 10,  # Default
                    "type": "reps"
                }

        # Map to Garmin exercise if we got a result
        if result:
            mapped, confidence = self.mapper.map_exercise(result["raw_name"])
            result["garmin_name"] = mapped["garmin_name"]
            result["garmin_category"] = mapped["garmin_category"]
            result["muscles"] = mapped.get("muscles", [])
            result["mapping_confidence"] = confidence

        return result

    def parse_workout(self, text: str, name: str = "Workout") -> Dict[str, Any]:
        """
        Parse a full workout from text.

        Args:
            text: Multi-line workout description
            name: Workout name

        Returns:
            Workout dict with exercises list
        """
        lines = text.strip().split('\n')
        exercises = []
        current_section = None
        warnings = []

        for line in lines:
            line = line.strip()

            # Check for section headers
            if line.endswith(':') or line.startswith('##'):
                current_section = line.rstrip(':').lstrip('#').strip()
                continue

            # Skip list markers
            if line.startswith(('- ', '• ', '* ', '1.', '2.', '3.', '4.', '5.')):
                line = re.sub(r'^[-•*]\s*', '', line)
                line = re.sub(r'^\d+\.\s*', '', line)

            # Parse the exercise
            exercise = self.parse_exercise_line(line)

            if exercise:
                exercise["section"] = current_section
                exercises.append(exercise)

                # Warn about low confidence mappings
                if exercise["mapping_confidence"] < 70:
                    warnings.append(
                        f"Low confidence mapping for '{exercise['raw_name']}' "
                        f"-> '{exercise['garmin_name']}' ({exercise['mapping_confidence']}%)"
                    )

        return {
            "name": name,
            "exercises": exercises,
            "exercise_count": len(exercises),
            "warnings": warnings
        }

    def to_garmin_format(self, workout: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert parsed workout to Garmin API format.
        Uses the correct RepeatGroupDTO structure that Garmin expects.

        Args:
            workout: Parsed workout dict

        Returns:
            Garmin-compatible workout structure
        """
        workout_steps = []
        step_order = 1

        for exercise in workout["exercises"]:
            sets = exercise.get("sets", 3)
            reps = exercise.get("reps", 10)
            category = exercise.get("garmin_category", "UNKNOWN")
            exercise_name = exercise.get("garmin_name", "UNKNOWN")

            # Handle duration-based exercises (like dead hangs)
            if exercise.get("type") == "duration":
                end_condition = {
                    "conditionTypeId": 2,
                    "conditionTypeKey": "time"
                }
                end_value = float(exercise.get("duration_seconds", 30))
            else:
                end_condition = {
                    "conditionTypeId": 10,
                    "conditionTypeKey": "reps"
                }
                end_value = float(reps)

            # Create RepeatGroupDTO for the exercise sets
            repeat_group = {
                "type": "RepeatGroupDTO",
                "stepOrder": step_order,
                "stepType": {
                    "stepTypeId": 6,
                    "stepTypeKey": "repeat"
                },
                "numberOfIterations": sets,
                "workoutSteps": [
                    {
                        "type": "ExecutableStepDTO",
                        "stepOrder": step_order + 1,
                        "stepType": {
                            "stepTypeId": 3,
                            "stepTypeKey": "interval"
                        },
                        "endCondition": end_condition,
                        "endConditionValue": end_value,
                        "targetType": {
                            "workoutTargetTypeId": 1,
                            "workoutTargetTypeKey": "no.target"
                        },
                        "category": category,
                        "exerciseName": exercise_name,
                        "weightValue": None,
                        "weightUnit": {
                            "unitId": 8,
                            "unitKey": "kilogram",
                            "factor": 1000.0
                        }
                    },
                    {
                        "type": "ExecutableStepDTO",
                        "stepOrder": step_order + 2,
                        "stepType": {
                            "stepTypeId": 5,
                            "stepTypeKey": "rest"
                        },
                        "endCondition": {
                            "conditionTypeId": 1,
                            "conditionTypeKey": "lap.button"
                        },
                        "endConditionValue": 0.0,
                        "targetType": {
                            "workoutTargetTypeId": 1,
                            "workoutTargetTypeKey": "no.target"
                        }
                    }
                ]
            }
            workout_steps.append(repeat_group)
            step_order += 3

        return {
            "workoutName": workout["name"],
            "description": f"Created via GarminCoach. {len(workout['exercises'])} exercises.",
            "sportType": {
                "sportTypeId": 5,
                "sportTypeKey": "strength_training"
            },
            "workoutSegments": [
                {
                    "segmentOrder": 1,
                    "sportType": {
                        "sportTypeId": 5,
                        "sportTypeKey": "strength_training"
                    },
                    "workoutSteps": workout_steps
                }
            ]
        }


def parse_workout_text(text: str, name: str = "Workout") -> Dict[str, Any]:
    """
    Convenience function to parse workout text.

    Args:
        text: Workout description
        name: Workout name

    Returns:
        Parsed and Garmin-formatted workout
    """
    parser = WorkoutParser()
    parsed = parser.parse_workout(text, name)
    garmin_format = parser.to_garmin_format(parsed)

    return {
        "parsed": parsed,
        "garmin_format": garmin_format
    }
