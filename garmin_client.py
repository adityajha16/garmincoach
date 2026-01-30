"""
Garmin Connect API client wrapper.
Handles authentication and provides methods for workout and activity management.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from garminconnect import Garmin
from dotenv import load_dotenv


class GarminClient:
    """Wrapper for Garmin Connect API interactions."""

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Garmin client.

        Args:
            email: Garmin account email (or set GARMIN_EMAIL env var)
            password: Garmin account password (or set GARMIN_PASSWORD env var)
        """
        load_dotenv()

        self.email = email or os.getenv("GARMIN_EMAIL")
        self.password = password or os.getenv("GARMIN_PASSWORD")

        if not self.email or not self.password:
            raise ValueError(
                "Garmin credentials not found. Set GARMIN_EMAIL and GARMIN_PASSWORD "
                "in .env file or pass them directly."
            )

        self.client: Optional[Garmin] = None
        self.token_path = Path(__file__).parent / ".garmin_tokens"

    def login(self) -> bool:
        """
        Authenticate with Garmin Connect.
        Uses cached tokens if available.

        Returns:
            True if login successful
        """
        try:
            self.client = Garmin(self.email, self.password)
            self.client.login()
            return True
        except Exception as e:
            raise ConnectionError(f"Failed to login to Garmin Connect: {e}")

    def ensure_connected(self):
        """Ensure client is connected, login if not."""
        if self.client is None:
            self.login()

    # ==================== WORKOUT METHODS ====================

    def list_workouts(self) -> List[Dict[str, Any]]:
        """
        Get all workouts from Garmin Connect.

        Returns:
            List of workout dictionaries
        """
        self.ensure_connected()
        try:
            workouts = self.client.get_workouts()
            return workouts if workouts else []
        except Exception as e:
            raise RuntimeError(f"Failed to fetch workouts: {e}")

    def get_workout(self, workout_id: str) -> Dict[str, Any]:
        """
        Get a specific workout by ID.

        Args:
            workout_id: The workout ID

        Returns:
            Workout dictionary
        """
        self.ensure_connected()
        try:
            return self.client.get_workout(workout_id)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch workout {workout_id}: {e}")

    def create_workout(self, workout_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new workout in Garmin Connect.

        Args:
            workout_data: Workout definition dictionary

        Returns:
            Created workout response
        """
        self.ensure_connected()
        try:
            # The garminconnect library should have upload_workout method
            result = self.client.upload_workout(workout_data)
            return result
        except AttributeError:
            # Fallback: try direct API call if method doesn't exist
            raise NotImplementedError(
                "Workout upload not available in current garminconnect version. "
                "May need to use alternative method."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create workout: {e}")

    def delete_workout(self, workout_id: str) -> bool:
        """
        Delete a workout from Garmin Connect.

        Args:
            workout_id: The workout ID to delete

        Returns:
            True if successful
        """
        self.ensure_connected()
        try:
            self.client.delete_workout(workout_id)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete workout {workout_id}: {e}")

    def schedule_workout(self, workout_id: str, date: str) -> Dict[str, Any]:
        """
        Schedule a workout on a specific date.

        Args:
            workout_id: The workout ID to schedule
            date: Date in YYYY-MM-DD format

        Returns:
            Scheduled workout response
        """
        self.ensure_connected()
        try:
            url = f"/workout-service/schedule/{workout_id}"
            payload = {"date": date}
            return self.client.garth.post("connectapi", url, json=payload, api=True).json()
        except Exception as e:
            raise RuntimeError(f"Failed to schedule workout {workout_id} on {date}: {e}")

    def get_scheduled_workouts(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Get scheduled workouts in a date range using calendar service.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of scheduled workouts
        """
        self.ensure_connected()
        try:
            from datetime import datetime
            # Parse dates to get year/month for calendar-service
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            scheduled = []
            # Iterate through months in range
            current = start
            seen_months = set()
            while current <= end:
                month_key = (current.year, current.month)
                if month_key not in seen_months:
                    seen_months.add(month_key)
                    # Calendar service uses 0-indexed months
                    url = f"/calendar-service/year/{current.year}/month/{current.month - 1}"
                    result = self.client.connectapi(url)
                    items = result.get("calendarItems", [])
                    # Filter for scheduled workouts (have workoutId but no activityId)
                    for item in items:
                        if item.get("workoutId") and item.get("itemType") == "workout":
                            item_date = item.get("date", "")
                            if start_date <= item_date <= end_date:
                                scheduled.append(item)
                # Move to next month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

            return sorted(scheduled, key=lambda x: x.get("date", ""))
        except Exception as e:
            raise RuntimeError(f"Failed to get scheduled workouts: {e}")

    # ==================== ACTIVITY METHODS ====================

    def get_activities(
        self,
        days: int = 30,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        activity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get activities from Garmin Connect.

        Args:
            days: Number of days to look back (default 30)
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            activity_type: Filter by activity type (e.g., 'running', 'strength_training')

        Returns:
            List of activity dictionaries
        """
        self.ensure_connected()
        try:
            if start_date and end_date:
                activities = self.client.get_activities_by_date(start_date, end_date)
            else:
                activities = self.client.get_activities(0, days * 3)  # Fetch more to account for rest days

            if activity_type:
                activities = [
                    a for a in activities
                    if activity_type.lower() in a.get("activityType", {}).get("typeKey", "").lower()
                ]

            return activities[:days * 2] if activities else []  # Reasonable limit
        except Exception as e:
            raise RuntimeError(f"Failed to fetch activities: {e}")

    def get_activity(self, activity_id: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific activity.

        Args:
            activity_id: The activity ID

        Returns:
            Activity details dictionary
        """
        self.ensure_connected()
        try:
            return self.client.get_activity(activity_id)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch activity {activity_id}: {e}")

    def get_activity_hr_zones(self, activity_id: str) -> Dict[str, Any]:
        """
        Get heart rate zones for a specific activity.

        Args:
            activity_id: The activity ID

        Returns:
            HR zones dictionary
        """
        self.ensure_connected()
        try:
            return self.client.get_activity_hr_in_timezones(activity_id)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch HR zones for {activity_id}: {e}")

    # ==================== HEALTH STATS METHODS ====================

    def get_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get daily health stats.

        Args:
            date: Date in YYYY-MM-DD format (default: today)

        Returns:
            Stats dictionary with sleep, steps, body battery, etc.
        """
        self.ensure_connected()

        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        stats = {}

        try:
            stats["sleep"] = self.client.get_sleep_data(date)
        except:
            stats["sleep"] = None

        try:
            stats["steps"] = self.client.get_steps_data(date)
        except:
            stats["steps"] = None

        try:
            stats["heart_rate"] = self.client.get_heart_rates(date)
        except:
            stats["heart_rate"] = None

        try:
            stats["body_battery"] = self.client.get_body_battery(date)
        except:
            stats["body_battery"] = None

        try:
            stats["stress"] = self.client.get_stress_data(date)
        except:
            stats["stress"] = None

        return stats

    # ==================== EXERCISE METHODS ====================

    def get_exercise_types(self) -> List[Dict[str, Any]]:
        """
        Get list of available exercise types from Garmin.

        Returns:
            List of exercise type dictionaries
        """
        self.ensure_connected()
        try:
            # This may need adjustment based on actual API
            return self.client.get_exercise_sets()
        except Exception as e:
            # Fallback - return empty if not available
            return []

    def search_exercises(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for exercises in Garmin's library.

        Args:
            query: Search term

        Returns:
            List of matching exercises
        """
        self.ensure_connected()
        try:
            # May need to implement based on actual API capabilities
            exercises = self.get_exercise_types()
            query_lower = query.lower()
            return [
                e for e in exercises
                if query_lower in str(e).lower()
            ]
        except Exception as e:
            return []


def build_strength_workout(
    name: str,
    exercises: List[Dict[str, Any]],
    description: str = ""
) -> Dict[str, Any]:
    """
    Build a Garmin strength workout structure matching the actual API format.

    Args:
        name: Workout name (e.g., "Pull Day")
        exercises: List of exercise dicts with keys:
            - name: Exercise name (Garmin format, e.g., "PULL_UP")
            - category: Exercise category (e.g., "PULL_UP")
            - sets: Number of sets
            - reps: Reps per set (or duration in seconds for holds)
        description: Optional workout description

    Returns:
        Workout dictionary ready for upload
    """
    workout_steps = []
    step_order = 1

    for exercise in exercises:
        sets = exercise.get("sets", 3)
        reps = exercise.get("reps", 10)
        category = exercise.get("category", "UNKNOWN")
        exercise_name = exercise.get("name", "UNKNOWN")

        # Create a RepeatGroupDTO for the exercise sets
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
                    "endCondition": {
                        "conditionTypeId": 10,
                        "conditionTypeKey": "reps"
                    },
                    "endConditionValue": float(reps),
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
        step_order += 3  # Increment for next exercise group

    workout = {
        "workoutName": name,
        "description": description or f"Created via GarminCoach. {len(exercises)} exercises.",
        "sportType": {
            "sportTypeId": 5,  # Strength training
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

    return workout
