import re
import logging
from fuzzywuzzy import process

logger = logging.getLogger(__name__)

def parse_predictions(text: str, markets: list) -> list:
    """
    Parse user prediction text and return list of (market_index, predicted_team, outcome) tuples.
    Supports 3 formats:
    1. Numbered: "19 Atlanta Yes" or "19 atlanta yes" (case-insensitive)
    2. Comma-separated: "Warriors Yes, Heat No, Lakers Yes"
    3. Line-break: "Warriors Yes" then "Heat No" then "Lakers Yes"
    """
    if not text or not markets:
        raise ValueError("No markets or prediction text provided")

    text = text.strip()
    predictions_text = []

    if "," in text:
        predictions_text = [p.strip() for p in text.split(",")]
    else:
        predictions_text = [p.strip() for p in text.split("\n") if p.strip()]

    if not predictions_text:
        raise ValueError("No predictions provided.")

    parsed = []
    market_map = {(m["team_a"].lower(), m["team_b"].lower()): i for i, m in enumerate(markets)}

    for pred_text in predictions_text:
        market_idx, predicted_team, outcome = _parse_single_prediction(pred_text, markets)
        parsed.append((market_idx, predicted_team, outcome))

    return parsed

def _parse_single_prediction(text: str, markets: list) -> tuple:
    """
    Parse a single prediction. Supports:
    - Numbered: "19 Atlanta Yes"
    - Unnumbered: "Atlanta Yes"
    Returns (market_index, team, outcome) tuple.
    """
    text = text.strip()
    words = text.split()

    if not words:
        raise ValueError("Empty prediction. Please use format: 'Team Yes' or '#Number Team Yes'")

    # Check if first word is a number (market index)
    market_idx = None
    team_start_idx = 0

    if words[0].isdigit():
        market_idx = int(words[0]) - 1  # Convert to 0-indexed
        team_start_idx = 1

        if market_idx < 0 or market_idx >= len(markets):
            raise ValueError(f"Market number {market_idx + 1} is out of range (1-{len(markets)})")

    # Get outcome (last word)
    if len(words) <= team_start_idx:
        raise ValueError("No team name found. Please use format: 'Team Yes' or '#Number Team Yes'")

    last_word = words[-1].lower()
    if last_word not in ["yes", "no"]:
        raise ValueError(f"Use 'Yes' or 'No' for prediction. Got: '{last_word}'")

    outcome = "Yes" if last_word == "yes" else "No"
    team_name = " ".join(words[team_start_idx:-1]).strip()

    if not team_name:
        raise ValueError("No team name found. Please use format: 'Team Yes' or '#Number Team Yes'")

    # If market_idx not provided, we can't determine which market this is for
    if market_idx is None:
        raise ValueError("Please specify market number (e.g., '19 Atlanta Yes') to avoid ambiguity")

    # Match team to the specified market
    market = markets[market_idx]
    matched_team = _match_team(team_name, (market["team_a"], market["team_b"]))

    if not matched_team:
        raise ValueError(
            f"Market {market_idx + 1}: Team '{team_name}' not found. "
            f"Did you mean '{market['team_a']}' or '{market['team_b']}'?"
        )

    return (market_idx, matched_team, outcome)

def _match_team(user_input: str, teams: tuple) -> str:
    """
    Match user team input to one of two teams.
    First tries exact match (case-insensitive), then fuzzy match.
    """
    team_a, team_b = teams
    user_lower = user_input.lower()
    team_a_lower = team_a.lower()
    team_b_lower = team_b.lower()

    if user_lower == team_a_lower:
        return team_a
    if user_lower == team_b_lower:
        return team_b

    candidates = [team_a, team_b]
    match = process.extractOne(user_input, candidates, score_cutoff=90)

    if match:
        return match[0]

    return None

def validate_predictions(predictions: list, markets: list) -> bool:
    """
    Validate that predictions match markets.
    Returns True if valid, raises ValueError otherwise.
    """
    if len(predictions) != len(markets):
        raise ValueError(f"Prediction count mismatch: expected {len(markets)}, got {len(predictions)}")

    for pred_team, outcome in predictions:
        if outcome not in ["Yes", "No"]:
            raise ValueError(f"Invalid outcome: '{outcome}'. Use 'Yes' or 'No'")

    return True
