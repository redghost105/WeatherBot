import requests
import logging
import time
import re
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class KalshiClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.max_retries = 3

    def _make_request(self, method: str, endpoint: str, **kwargs):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = kwargs.pop("headers", {})

        if self.api_key and self.api_secret:
            headers["Authorization"] = f"Bearer {self.api_key}"

        headers["Content-Type"] = "application/json"

        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=headers,
                    auth=HTTPBasicAuth(self.api_key, self.api_secret) if self.api_key else None,
                    timeout=10,
                    **kwargs
                )

                if response.status_code == 401:
                    logger.error(f"Auth error: {response.status_code} {response.text}")
                    raise ValueError("Invalid Kalshi API credentials")

                if response.status_code in [429, 503]:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited ({response.status_code}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()
                return response.json()

            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Request failed after {self.max_retries} attempts: {e}")
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"Request failed, retrying in {wait_time}s...")
                time.sleep(wait_time)

    def get_playoff_markets(self) -> List[Dict]:
        try:
            # Series for Games, Series, and Futures categories
            playoff_series_list = [
                ("Games", "KXNBAGAME"),           # NBA games
                ("Playoffs", "KXNBAPLAYOFF"),      # Playoff Qualifier
                ("Series", "KXNBAPLAYOFFPTS"),     # Playoff Points
                ("Futures", "KXNBAMVP"),           # MVP and awards
            ]

            result = []
            exclude_statuses = ["resolved", "cancelled", "no_contest"]

            for category, series_ticker in playoff_series_list:
                logger.info(f"Fetching {category} from series: {series_ticker}")

                try:
                    # Get events with nested markets
                    events_data = self._make_request(
                        "GET",
                        "events",
                        params={
                            "series_ticker": series_ticker,
                            "limit": 100,
                            "with_nested_markets": "true"
                        }
                    )
                    events = events_data.get("events", [])

                    if not events:
                        logger.warning(f"No events found for {category} series")
                        continue

                    logger.info(f"Found {len(events)} {category} events")

                    for event in events:
                        event_title = event.get("title", "")
                        markets_list = event.get("markets", [])

                        if not markets_list:
                            event_ticker = event.get("ticker")
                            if event_ticker:
                                try:
                                    markets_data = self._make_request("GET", "markets", params={"event_ticker": event_ticker})
                                    markets_list = markets_data.get("markets", [])
                                except Exception as e:
                                    logger.warning(f"Failed to fetch markets for event {event_ticker}: {e}")
                                    continue

                        for market in markets_list:
                            if market.get("status") in exclude_statuses:
                                continue

                            market_ticker = market.get("ticker")
                            title = market.get("title", "")
                            subtitle = market.get("subtitle", "")

                            # Extract teams from event title first (better for games)
                            team_a, team_b = self._extract_teams(event_title, "")
                            if not team_a or not team_b:
                                team_a, team_b = self._extract_teams(title, subtitle)

                            if team_a and team_b:
                                result.append({
                                    "market_id": market_ticker,
                                    "team_a": team_a,
                                    "team_b": team_b,
                                    "status": market.get("status"),
                                    "title": title,
                                    "category": category
                                })

                except Exception as e:
                    logger.warning(f"Failed to fetch {category} series {series_ticker}: {e}")
                    continue

            logger.info(f"Fetched {len(result)} active NBA Playoffs markets from all categories")
            return result

        except Exception as e:
            logger.error(f"Failed to fetch playoff markets: {e}")
            raise

    def get_market_result(self, market_id: str) -> Optional[Dict]:
        try:
            # market_id is now a ticker (e.g., "PROF-LAKERS-1-YES")
            data = self._make_request("GET", f"markets/{market_id}")
            market = data.get("market", {})

            result_str = market.get("result")
            status = market.get("status")

            return {
                "result": result_str,
                "status": status
            }
        except Exception as e:
            logger.error(f"Failed to fetch market result for {market_id}: {e}")
            return None

    def format_market_display(self, markets: List[Dict], start_number: int = 1) -> str:
        if not markets:
            return "No active NBA Playoffs markets at the moment."

        lines = ["🏀 **NBA Playoffs Markets** 🏀", ""]

        for i, market in enumerate(markets, start_number):
            lines.append(f"{i}. {market['team_a']} vs {market['team_b']}")

        lines.extend([
            "",
            "Reply with your predictions (e.g., \"Warriors Yes, Heat No, Lakers Yes\")",
            "or on separate lines:",
            "Warriors Yes",
            "Heat No",
            "Lakers Yes"
        ])

        return "\n".join(lines)

    def _extract_teams(self, title: str, subtitle: str = "") -> tuple:
        patterns = [
            r"Will the ([\w\s]+?)\s+(?:beat|win over|defeat)\s+(?:the\s+)?([\w\s]+?)(?:\?|$)",
            r"([\w\s]+?)\s+(?:vs|vs\.)\s+([\w\s]+?)(?:\?|$)",
            r"([\w\s]+?)\s+at\s+([\w\s]+?)(?:\?|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                team_a = match.group(1).strip()
                team_b = match.group(2).strip()
                # Clean up extra words (remove "the", "be", etc)
                team_a = re.sub(r'\b(the|be|will)\b', '', team_a, flags=re.IGNORECASE).strip()
                team_b = re.sub(r'\b(the|be|will)\b', '', team_b, flags=re.IGNORECASE).strip()
                if team_a and team_b:
                    return team_a, team_b

        if " vs " in subtitle:
            parts = subtitle.split(" vs ")
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()

        return None, None
