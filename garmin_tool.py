#!/usr/bin/env python3
"""
Garmin Coach CLI Tool
A command-line interface for managing Garmin Connect workouts and activities.

Usage:
    python garmin_tool.py <command> [options]

Commands:
    create-workout    Create a new strength workout
    list-workouts     List all workouts
    get-workout       Get workout details
    delete-workout    Delete a workout
    get-activities    Get recent activities
    get-activity      Get activity details
    get-stats         Get daily health stats
    search-exercise   Search exercise database
    parse-workout     Parse workout text (dry run)
"""

import json
import sys
from datetime import datetime, timedelta
from typing import Optional

import click

from garmin_client import GarminClient, build_strength_workout
from exercise_mapper import ExerciseMapper
from workout_parser import WorkoutParser, parse_workout_text


# Initialize shared objects
client = None
mapper = ExerciseMapper()
parser = WorkoutParser()


def get_client() -> GarminClient:
    """Get or create Garmin client instance."""
    global client
    if client is None:
        client = GarminClient()
        client.login()
    return client


def output_json(data, pretty=True):
    """Output data as JSON."""
    if pretty:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        click.echo(json.dumps(data, default=str))


@click.group()
@click.option('--json-output', '-j', is_flag=True, help='Output as JSON')
@click.pass_context
def cli(ctx, json_output):
    """Garmin Coach CLI - Manage workouts and track fitness data."""
    ctx.ensure_object(dict)
    ctx.obj['json'] = json_output


# ==================== WORKOUT COMMANDS ====================

@cli.command('create-workout')
@click.option('--name', '-n', required=True, help='Workout name')
@click.option('--exercises', '-e', help='Exercises as JSON array')
@click.option('--text', '-t', help='Workout as plain text')
@click.option('--file', '-f', type=click.Path(exists=True), help='Read workout from file')
@click.option('--dry-run', is_flag=True, help='Parse only, do not upload')
@click.pass_context
def create_workout(ctx, name, exercises, text, file, dry_run):
    """
    Create a new strength workout.

    Examples:
        # From JSON exercises
        python garmin_tool.py create-workout -n "Pull Day" -e '[{"name":"Pull Up","sets":4,"reps":8}]'

        # From plain text
        python garmin_tool.py create-workout -n "Pull Day" -t "4x8 Pull-ups
        4x10 Barbell Rows
        3x12 Lat Pulldowns"

        # From file
        python garmin_tool.py create-workout -n "Pull Day" -f workout.txt
    """
    workout_data = None

    # Parse from file
    if file:
        with open(file, 'r') as f:
            text = f.read()

    # Parse from plain text
    if text:
        result = parse_workout_text(text, name)
        parsed = result["parsed"]
        workout_data = result["garmin_format"]

        # Show parsing results
        click.echo(f"Parsed {parsed['exercise_count']} exercises:")
        for ex in parsed["exercises"]:
            conf_indicator = "✓" if ex["mapping_confidence"] >= 70 else "?"
            click.echo(f"  {conf_indicator} {ex['raw_name']} -> {ex['garmin_name']} "
                      f"({ex['sets']}x{ex.get('reps', ex.get('duration_seconds', '?'))})")

        if parsed["warnings"]:
            click.echo("\nWarnings:")
            for w in parsed["warnings"]:
                click.echo(f"  ⚠ {w}")

    # Parse from JSON exercises
    elif exercises:
        try:
            exercise_list = json.loads(exercises)
            # Map exercise names to Garmin format
            mapped_exercises = []
            for ex in exercise_list:
                mapped, conf = mapper.map_exercise(ex.get("name", ex.get("exercise", "")))
                mapped_exercises.append({
                    "name": mapped["garmin_name"],
                    "category": mapped["garmin_category"],
                    "sets": ex.get("sets", 3),
                    "reps": ex.get("reps", 10)
                })
            workout_data = build_strength_workout(name, mapped_exercises)
        except json.JSONDecodeError as e:
            click.echo(f"Error: Invalid JSON - {e}", err=True)
            sys.exit(1)

    if not workout_data:
        click.echo("Error: Provide --exercises, --text, or --file", err=True)
        sys.exit(1)

    if dry_run:
        click.echo("\n[DRY RUN] Would create workout:")
        output_json(workout_data)
        return

    # Upload to Garmin
    try:
        gc = get_client()
        result = gc.create_workout(workout_data)
        click.echo(f"\n✓ Workout '{name}' created successfully!")
        if ctx.obj.get('json'):
            output_json(result)
    except Exception as e:
        click.echo(f"Error creating workout: {e}", err=True)
        sys.exit(1)


@cli.command('list-workouts')
@click.option('--limit', '-l', default=20, help='Maximum workouts to show')
@click.pass_context
def list_workouts(ctx, limit):
    """List all workouts in Garmin Connect."""
    try:
        gc = get_client()
        workouts = gc.list_workouts()

        if ctx.obj.get('json'):
            output_json(workouts[:limit])
            return

        if not workouts:
            click.echo("No workouts found.")
            return

        click.echo(f"Found {len(workouts)} workouts:\n")
        for w in workouts[:limit]:
            workout_id = w.get("workoutId", "?")
            name = w.get("workoutName", "Unnamed")
            sport = w.get("sportType", {}).get("sportTypeKey", "?")
            click.echo(f"  [{workout_id}] {name} ({sport})")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command('get-workout')
@click.argument('workout_id')
@click.pass_context
def get_workout(ctx, workout_id):
    """Get details of a specific workout."""
    try:
        gc = get_client()
        workout = gc.get_workout(workout_id)
        output_json(workout)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command('delete-workout')
@click.argument('workout_id')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
def delete_workout(workout_id, yes):
    """Delete a workout from Garmin Connect."""
    if not yes:
        click.confirm(f"Delete workout {workout_id}?", abort=True)

    try:
        gc = get_client()
        gc.delete_workout(workout_id)
        click.echo(f"✓ Workout {workout_id} deleted.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ==================== ACTIVITY COMMANDS ====================

@cli.command('get-activities')
@click.option('--days', '-d', default=30, help='Number of days to look back')
@click.option('--type', '-t', 'activity_type', help='Filter by type (running, strength_training)')
@click.option('--start', help='Start date (YYYY-MM-DD)')
@click.option('--end', help='End date (YYYY-MM-DD)')
@click.pass_context
def get_activities(ctx, days, activity_type, start, end):
    """Get recent activities."""
    try:
        gc = get_client()
        activities = gc.get_activities(
            days=days,
            start_date=start,
            end_date=end,
            activity_type=activity_type
        )

        if ctx.obj.get('json'):
            output_json(activities)
            return

        if not activities:
            click.echo("No activities found.")
            return

        click.echo(f"Found {len(activities)} activities:\n")
        for a in activities:
            activity_id = a.get("activityId", "?")
            name = a.get("activityName", "Unnamed")
            activity_type_name = a.get("activityType", {}).get("typeKey", "?")
            start_time = a.get("startTimeLocal", "?")
            duration = a.get("duration", 0)
            duration_min = int(duration / 60) if duration else 0

            click.echo(f"  [{activity_id}] {start_time[:10]} - {name}")
            click.echo(f"      Type: {activity_type_name}, Duration: {duration_min} min")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command('get-activity')
@click.argument('activity_id')
@click.option('--hr-zones', is_flag=True, help='Include HR zone breakdown')
@click.pass_context
def get_activity(ctx, activity_id, hr_zones):
    """Get details of a specific activity."""
    try:
        gc = get_client()
        activity = gc.get_activity(activity_id)

        if hr_zones:
            try:
                zones = gc.get_activity_hr_zones(activity_id)
                activity["hrZones"] = zones
            except:
                pass

        output_json(activity)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ==================== HEALTH STATS COMMANDS ====================

@cli.command('get-stats')
@click.option('--date', '-d', default='today', help='Date (YYYY-MM-DD or "today")')
@click.pass_context
def get_stats(ctx, date):
    """Get daily health stats (sleep, steps, body battery)."""
    if date == 'today':
        date = datetime.now().strftime("%Y-%m-%d")

    try:
        gc = get_client()
        stats = gc.get_stats(date)

        if ctx.obj.get('json'):
            output_json(stats)
            return

        click.echo(f"Stats for {date}:\n")

        # Sleep
        if stats.get("sleep"):
            sleep = stats["sleep"]
            click.echo(f"  Sleep: {sleep.get('sleepTimeSeconds', 0) / 3600:.1f} hours")

        # Steps
        if stats.get("steps"):
            steps = stats["steps"]
            click.echo(f"  Steps: {steps.get('totalSteps', 0):,}")

        # Body Battery
        if stats.get("body_battery"):
            bb = stats["body_battery"]
            if isinstance(bb, list) and bb:
                latest = bb[-1] if bb else {}
                click.echo(f"  Body Battery: {latest.get('bodyBatteryLevel', '?')}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ==================== EXERCISE COMMANDS ====================

@cli.command('search-exercise')
@click.argument('query')
@click.option('--limit', '-l', default=5, help='Max results')
@click.pass_context
def search_exercise(ctx, query, limit):
    """Search for exercises in the mapping database."""
    matches = mapper.search(query, limit=limit)

    if ctx.obj.get('json'):
        results = []
        for name, score in matches:
            exercise = mapper.exercise_map.get(name, {})
            results.append({
                "name": name,
                "garmin_name": exercise.get("garmin_name"),
                "category": exercise.get("garmin_category"),
                "score": score
            })
        output_json(results)
        return

    if not matches:
        click.echo(f"No exercises found matching '{query}'")
        return

    click.echo(f"Exercises matching '{query}':\n")
    for name, score in matches:
        exercise = mapper.exercise_map.get(name, {})
        click.echo(f"  [{score}%] {name}")
        click.echo(f"      Garmin: {exercise.get('garmin_name')} ({exercise.get('garmin_category')})")


@cli.command('schedule-workout')
@click.argument('workout_name')
@click.option('--day', '-d', required=True,
              type=click.Choice(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']),
              help='Day of week to schedule')
@click.option('--weeks', '-w', default=8, help='Number of weeks to schedule (default: 8)')
@click.pass_context
def schedule_workout(ctx, workout_name, day, weeks):
    """
    Schedule a workout on a specific day of the week.

    Examples:
        python garmin_tool.py schedule-workout "Monday Push" --day monday --weeks 8
        python garmin_tool.py schedule-workout "Wednesday Pull" -d wednesday -w 4
    """
    from datetime import datetime, timedelta

    try:
        gc = get_client()
        workouts = gc.list_workouts()

        # Find workout by name (case-insensitive partial match)
        matching = [w for w in workouts if workout_name.lower() in w.get("workoutName", "").lower()]

        if not matching:
            click.echo(f"Error: No workout found matching '{workout_name}'", err=True)
            click.echo("Available workouts:")
            for w in workouts[:10]:
                click.echo(f"  - {w.get('workoutName')}")
            sys.exit(1)

        if len(matching) > 1:
            # Try exact match first
            exact = [w for w in matching if w.get("workoutName", "").lower() == workout_name.lower()]
            if exact:
                matching = exact
            else:
                click.echo(f"Multiple workouts match '{workout_name}':")
                for w in matching:
                    click.echo(f"  - {w.get('workoutName')}")
                click.echo("Please be more specific.")
                sys.exit(1)

        workout = matching[0]
        workout_id = workout.get("workoutId")
        workout_display_name = workout.get("workoutName")

        click.echo(f"Scheduling '{workout_display_name}' for {weeks} {day}s...")

        # Calculate dates for the specified day of week
        day_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        target_day = day_map[day]
        today = datetime.now()

        # Find next occurrence of the target day
        days_ahead = target_day - today.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7

        next_date = today + timedelta(days=days_ahead)

        # Schedule for specified number of weeks
        scheduled_count = 0
        for i in range(weeks):
            schedule_date = next_date + timedelta(weeks=i)
            date_str = schedule_date.strftime("%Y-%m-%d")

            try:
                gc.schedule_workout(workout_id, date_str)
                click.echo(f"  ✓ Scheduled for {date_str} ({schedule_date.strftime('%A')})")
                scheduled_count += 1
            except Exception as e:
                click.echo(f"  ✗ Failed for {date_str}: {e}")

        click.echo(f"\nScheduled {scheduled_count}/{weeks} instances of '{workout_display_name}'")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command('list-scheduled')
@click.option('--weeks', '-w', default=4, help='Number of weeks ahead to show (default: 4)')
@click.pass_context
def list_scheduled(ctx, weeks):
    """List scheduled workouts."""
    from datetime import datetime, timedelta

    try:
        gc = get_client()
        start = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(weeks=weeks)).strftime("%Y-%m-%d")

        scheduled = gc.get_scheduled_workouts(start, end)

        if ctx.obj.get('json'):
            output_json(scheduled)
            return

        if not scheduled:
            click.echo("No scheduled workouts found.")
            return

        click.echo(f"Scheduled workouts ({start} to {end}):\n")
        for s in scheduled:
            date = s.get("date", "?")
            name = s.get("title", s.get("workoutName", "?"))
            click.echo(f"  {date}: {name}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command('parse-workout')
@click.option('--text', '-t', help='Workout text to parse')
@click.option('--file', '-f', type=click.Path(exists=True), help='Read from file')
@click.option('--name', '-n', default='Test Workout', help='Workout name')
@click.pass_context
def parse_workout_cmd(ctx, text, file, name):
    """Parse workout text without uploading (dry run)."""
    if file:
        with open(file, 'r') as f:
            text = f.read()

    if not text:
        click.echo("Error: Provide --text or --file", err=True)
        sys.exit(1)

    result = parse_workout_text(text, name)

    if ctx.obj.get('json'):
        output_json(result)
        return

    parsed = result["parsed"]
    click.echo(f"Parsed '{name}' - {parsed['exercise_count']} exercises:\n")

    for ex in parsed["exercises"]:
        conf = ex["mapping_confidence"]
        indicator = "✓" if conf >= 70 else "?" if conf >= 50 else "✗"

        if ex.get("type") == "duration":
            detail = f"{ex['sets']}x{ex['duration_seconds']}s"
        else:
            detail = f"{ex['sets']}x{ex['reps']}"

        click.echo(f"  {indicator} {ex['raw_name']}")
        click.echo(f"      -> {ex['garmin_name']} ({detail}) [{conf}% confidence]")

    if parsed["warnings"]:
        click.echo("\nWarnings:")
        for w in parsed["warnings"]:
            click.echo(f"  ⚠ {w}")


if __name__ == '__main__':
    cli(obj={})
