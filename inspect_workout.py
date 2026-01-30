#!/usr/bin/env python3
"""Inspect workout format from Garmin."""
import json
import os
from garminconnect import Garmin
from dotenv import load_dotenv

load_dotenv()

client = Garmin(os.getenv("GARMIN_EMAIL"), os.getenv("GARMIN_PASSWORD"))
client.login()

# Get workout methods
methods = [m for m in dir(client) if 'workout' in m.lower()]
print("Workout methods:", methods)

# Get workouts list
workouts = client.get_workouts()
if workouts:
    print(f"\nFound {len(workouts)} workouts")

    # Get full workout details by ID
    workout_id = workouts[0]["workoutId"]
    print(f"\nFetching full details for workout {workout_id}...")
    full_workout = client.get_workout_by_id(workout_id)
    print("\nFull workout structure:")
    print(json.dumps(full_workout, indent=2, default=str))
