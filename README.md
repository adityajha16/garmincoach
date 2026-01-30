# GarminCoach

CLI tool for creating and managing Garmin Connect strength workouts.

## Features

- Create strength workouts from simple text format
- Fuzzy matching for exercise names
- Parse and preview workouts before uploading
- Search Garmin exercise database
- Get activities and stats from Garmin Connect

## Installation

```bash
# Clone the repository
git clone git@github.com:adityajha-ezora/garmincoach.git
cd garmincoach

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up credentials
cp .env.example .env
# Edit .env with your Garmin Connect credentials
```

## Configuration

Create a `.env` file with your Garmin Connect credentials:

```
GARMIN_EMAIL=your_email@example.com
GARMIN_PASSWORD=your_password
```

## Usage

### Create Workout

```bash
python garmin_tool.py create-workout --name "My Workout" --text "4x8 Bench Press
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

## Common Exercise Mappings

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

## Files

```
garmin_tool.py      - Main CLI
garmin_client.py    - API wrapper
workout_parser.py   - Text parser
exercise_mapper.py  - Fuzzy matching
exercise_map.json   - Exercise mappings
```

## Troubleshooting

**400 Bad Request**: Check exercise name is valid. Some exercises (like DIPS) aren't accepted by Garmin.

**500 Server Error**: Usually wrong JSON structure.

**Login fails**: Check `.env` credentials. Garmin may require re-authentication.

## API Limitations

- No delete via API - must delete workouts manually in Garmin Connect
- Exercise names must match Garmin's database - check `exercise_map.json`
- Some exercises (like DIPS) fail - use alternatives like "Bench Dip"

## License

MIT
