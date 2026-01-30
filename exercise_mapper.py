"""
Exercise name mapping to Garmin exercise IDs.
Uses static mapping with fuzzy search fallback.
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from thefuzz import fuzz, process


class ExerciseMapper:
    """Maps exercise names to Garmin exercise format."""

    def __init__(self, map_file: Optional[Path] = None):
        """
        Initialize exercise mapper.

        Args:
            map_file: Path to exercise_map.json (default: same directory)
        """
        if map_file is None:
            map_file = Path(__file__).parent / "exercise_map.json"

        self.map_file = map_file
        self.exercise_map: Dict[str, Dict[str, Any]] = {}
        self._load_map()

    def _load_map(self):
        """Load exercise mappings from JSON file."""
        try:
            with open(self.map_file, "r") as f:
                data = json.load(f)
                self.exercise_map = data.get("exercises", {})
        except FileNotFoundError:
            print(f"Warning: Exercise map not found at {self.map_file}")
            self.exercise_map = {}
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in exercise map: {e}")
            self.exercise_map = {}

    def _normalize_name(self, name: str) -> str:
        """
        Normalize exercise name for matching.

        Args:
            name: Raw exercise name

        Returns:
            Normalized lowercase name
        """
        # Lowercase
        name = name.lower().strip()

        # Remove common variations
        name = re.sub(r'\s+', ' ', name)  # Multiple spaces to single
        name = re.sub(r'[^\w\s-]', '', name)  # Remove special chars except hyphen

        return name

    def map_exercise(self, name: str) -> Tuple[Dict[str, Any], int]:
        """
        Map an exercise name to Garmin format.

        Args:
            name: Exercise name (e.g., "Pull-ups", "Barbell Row")

        Returns:
            Tuple of (exercise_dict, confidence_score)
            exercise_dict has keys: garmin_name, garmin_category, muscles
            confidence_score: 100 for exact match, lower for fuzzy
        """
        normalized = self._normalize_name(name)

        # Try exact match first
        if normalized in self.exercise_map:
            return self.exercise_map[normalized], 100

        # Try fuzzy matching against all known exercises
        if self.exercise_map:
            matches = process.extractBests(
                normalized,
                self.exercise_map.keys(),
                scorer=fuzz.token_sort_ratio,
                limit=3
            )

            if matches and matches[0][1] >= 70:  # 70% confidence threshold
                best_match = matches[0][0]
                confidence = matches[0][1]
                return self.exercise_map[best_match], confidence

        # Return unknown exercise format
        return {
            "garmin_name": self._to_garmin_format(name),
            "garmin_category": "UNKNOWN",
            "muscles": []
        }, 0

    def _to_garmin_format(self, name: str) -> str:
        """
        Convert exercise name to GARMIN_FORMAT.

        Args:
            name: Human readable name

        Returns:
            UPPER_SNAKE_CASE format
        """
        # Remove special characters, replace spaces/hyphens with underscore
        formatted = re.sub(r'[^\w\s-]', '', name)
        formatted = re.sub(r'[\s-]+', '_', formatted)
        return formatted.upper()

    def add_mapping(self, name: str, garmin_name: str, category: str, muscles: List[str] = None):
        """
        Add a new exercise mapping.

        Args:
            name: Common exercise name
            garmin_name: Garmin exercise name key
            category: Garmin category key
            muscles: List of muscles worked
        """
        normalized = self._normalize_name(name)
        self.exercise_map[normalized] = {
            "garmin_name": garmin_name,
            "garmin_category": category,
            "muscles": muscles or []
        }
        self._save_map()

    def _save_map(self):
        """Save exercise mappings back to JSON file."""
        data = {
            "_comment": "Maps common exercise names to Garmin exercise categories and names",
            "_usage": "Keys are lowercase normalized names, values have garmin_name and category",
            "exercises": self.exercise_map
        }
        with open(self.map_file, "w") as f:
            json.dump(data, f, indent=2)

    def list_exercises(self) -> List[str]:
        """
        Get list of all mapped exercise names.

        Returns:
            List of exercise names
        """
        return list(self.exercise_map.keys())

    def search(self, query: str, limit: int = 5) -> List[Tuple[str, int]]:
        """
        Search for exercises matching a query.

        Args:
            query: Search term
            limit: Maximum results

        Returns:
            List of (exercise_name, match_score) tuples
        """
        if not self.exercise_map:
            return []

        normalized = self._normalize_name(query)
        matches = process.extractBests(
            normalized,
            self.exercise_map.keys(),
            scorer=fuzz.token_sort_ratio,
            limit=limit
        )
        return matches


# Convenience function
def map_exercise_name(name: str) -> Dict[str, Any]:
    """
    Quick function to map a single exercise name.

    Args:
        name: Exercise name

    Returns:
        Garmin exercise dict
    """
    mapper = ExerciseMapper()
    result, confidence = mapper.map_exercise(name)
    result["confidence"] = confidence
    return result
