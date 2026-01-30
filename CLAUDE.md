# GarminCoach - Claude Instructions

Tool for creating and managing Garmin Connect strength workouts via CLI.

## Setup

```bash
cd /Users/adityajha/projects/garmincoach
source venv/bin/activate
```

Credentials in `.env` (already configured).

## Commands

### Create Workout
```bash
python garmin_tool.py create-workout --name "Workout Name" --text "4x8 Bench Press
3x10 Pull-ups
2x30 sec Dead hang"
```

### List Workouts
```bash
python garmin_tool.py list-workouts --limit 10
```

### Parse Only (Preview)
```bash
python garmin_tool.py parse-workout --text "4x8 Bench Press"
```

### Search Exercise
```bash
python garmin_tool.py search-exercise "pull up"
```

### Get Activities
```bash
python garmin_tool.py get-activities --days 30
python garmin_tool.py get-activities --type strength_training
```

### Get Stats
```bash
python garmin_tool.py get-stats --date 2025-01-08
```

## Exercise Format

Supported patterns:
- `4x8 Bench Press` - sets x reps name
- `Bench Press 4x8` - name sets x reps
- `2x30 sec Dead hang` - duration-based
- `3 sets of Push-ups` - verbose

## Current Workouts (Matching Plan)

| Garmin Name | Day | Content |
|-------------|-----|---------|
| Monday Push | Mon | Bench 4x6, OHP 3x6, Incline DB 3x8, Push-ups 2x10 |
| Wednesday Pull | Wed | Scap pulls, Band pull-ups, Negatives, Dead hang, Assisted pull-ups, Row, RDL, Farmer carry |
| Friday Legs | Fri | Dead hang, Scap pulls, Squat 4x6, RDL 4x8, Lunges 3x8, Calf raises 2x15 |

## User's Training Protocol

**Primary Objective**: Follow the protocol properly.

### Running: Zone 2 Focus (Jan 2026+)
- Using Polar HRM chest strap for accurate HR data
- Zones set based on lactate threshold test (Jan 29, 2026)
- **Zone 2 (Base) ceiling: 147 bpm** - keep avg HR under this for easy runs
- Previous max HR setting (212) was incorrect - now properly calibrated
- Focus on aerobic base building with true Zone 2 runs

### Strength: Original Plan (Pull-up Focus)
```
MONDAY    - Push (strength) - use "Monday Push"
WEDNESDAY - Pull + pull-ups - use "Wednesday Pull"
FRIDAY    - Legs + mini pull-ups - use "Friday Legs"
```

**Goal**: 10 clean pull-ups in 4 months

### When Analyzing Performance
- Compare pace at same HR to track aerobic improvement
- Zone 2 runs: check avg HR stayed under 147 bpm
- Track training effect label (should be "BASE" for easy runs)
- Flag if vigorous intensity minutes are high on easy run days

## API Limitations

- **No delete via API** - user must delete workouts manually in Garmin Connect
- **Activity details available** - use `get-activity <id>` for full HR, pace, training effect data
- **Exercise names must match Garmin's** - check `exercise_map.json` for mappings
- **DIPS exercise fails** - use "Incline Dumbbell Press" or "Bench Dip" instead

## Exercise Map

Common exercises in `exercise_map.json`:

| Input | Garmin Name |
|-------|-------------|
| bench press | BENCH_PRESS |
| overhead press | OVERHEAD_PRESS |
| push-ups | PUSH_UP |
| pull-ups | PULL_UP |
| assisted pull-ups | ASSISTED_PULL_UP |
| barbell row | BARBELL_ROW |
| deadlift | DEADLIFT |
| romanian deadlift | ROMANIAN_DEADLIFT |
| squat | BARBELL_SQUAT |
| dead hang | DEAD_HANG |
| farmer carry | FARMERS_WALK |
| scap pulls | SCAPULAR_PULL_UP |
| calf raises | CALF_RAISE |
| walking lunge | WALKING_LUNGE |

## Troubleshooting

**400 Bad Request**: Check exercise name is valid. Some exercises (like DIPS) aren't accepted.

**500 Server Error**: Usually wrong JSON structure. The current format uses `RepeatGroupDTO` with nested `ExecutableStepDTO`.

**Login fails**: Check `.env` credentials. Garmin may require re-authentication.

## Files

```
garmin_tool.py      - Main CLI
garmin_client.py    - API wrapper
workout_parser.py   - Text parser
exercise_mapper.py  - Fuzzy matching
exercise_map.json   - Exercise mappings
```
