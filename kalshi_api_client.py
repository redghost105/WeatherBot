"""
Kalshi API Client for fetching real market prices and orderbook data.

Handles RSA-based authentication and provides methods to fetch:
- Market listings
- Orderbook prices for specific markets
- Temperature contract mappings
"""

import json
import logging
import requests
from typing import Dict, Optional, List
from datetime import datetime
import base64
import time
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class KalshiAPIClient:
    """
    Client for Kalshi Trade API v2.

    Handles authentication via RSA-signed requests and provides
    methods to fetch market data, orderbooks, and portfolio info.

    Two base URLs:
    - external-api.kalshi.com: Public market data (no auth required)
    - trading-api.kalshi.com: Authenticated portfolio endpoints (requires auth)
    """

    BASE_URL_PUBLIC = "https://external-api.kalshi.com/trade-api/v2"
    BASE_URL_TRADING = "https://api.elections.kalshi.com/trade-api/v2"  # New endpoint as of 2026
    BASE_URL = BASE_URL_PUBLIC  # Default for backward compatibility

    def __init__(self, api_key_id: str, private_key_pem: str):
        """
        Initialize Kalshi API client.

        Args:
            api_key_id: API key identifier (UUID)
            private_key_pem: RSA private key in PEM format
        """
        self.api_key_id = api_key_id
        self.private_key_pem = private_key_pem

        # Load private key
        try:
            self.private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None,
                backend=default_backend()
            )
            logger.info(f"✓ Loaded RSA private key for {api_key_id}")
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            raise

    def _sign_request(self, method: str, path: str, timestamp_ms: int) -> str:
        """
        Sign a request using RSA-PSS-SHA256.

        Kalshi requires signature format: {timestamp}{method}{path} (NO NEWLINES)

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path without query params (e.g., "/trade-api/v2/portfolio/orders")
            timestamp_ms: Current timestamp in milliseconds

        Returns:
            Base64-encoded RSA-PSS signature
        """
        # Signature string: TIMESTAMPMETHODPATH (concatenated, NO NEWLINES!)
        signature_string = f"{timestamp_ms}{method}{path}"

        # Sign with RSA-PSS-SHA256 (Kalshi uses PSS, not PKCS1v15)
        signature = self.private_key.sign(
            signature_string.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        # Return base64-encoded signature
        return base64.b64encode(signature).decode()

    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """
        Make an authenticated request to Kalshi API.

        Routes to correct base URL:
        - Portfolio endpoints → trading-api.kalshi.com
        - Market data endpoints → external-api.kalshi.com

        Args:
            method: HTTP method
            endpoint: API endpoint (e.g., "/markets" or "/portfolio/orders")
            data: Request body (for POST/PUT/DELETE)

        Returns:
            Response JSON
        """
        # Use trading API for portfolio endpoints, public API for market data
        if endpoint.startswith("/portfolio") or endpoint.startswith("/account"):
            base_url = self.BASE_URL_TRADING
        else:
            base_url = self.BASE_URL_PUBLIC

        url = f"{base_url}{endpoint}"

        # Get current timestamp in milliseconds
        timestamp_ms = int(time.time() * 1000)

        # Strip query parameters for signature (sign path only)
        path_for_signature = f"/trade-api/v2{endpoint.split('?')[0]}"

        # Create signature with timestamp
        signature = self._sign_request(method, path_for_signature, timestamp_ms)

        # Build headers with correct Kalshi authentication
        headers = {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-TIMESTAMP": str(timestamp_ms),
            "KALSHI-ACCESS-SIGNATURE": signature,
        }

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=10)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed ({method} {url}): {e}")
            return {}

    def get_markets(self, status: Optional[str] = "open", series_ticker: Optional[str] = None) -> List[Dict]:
        """
        Fetch markets list filtered by status and/or series ticker.

        Args:
            status: Market status filter (unopened, open, closed, settled)
            series_ticker: Series ticker for filtering (e.g., "KXHIGHNY" for NYC temperature)

        Returns:
            List of market objects
        """
        params_list = []
        if status:
            params_list.append(f"status={status}")
        if series_ticker:
            params_list.append(f"series_ticker={series_ticker}")

        params = "?" + "&".join(params_list) if params_list else ""
        response = self._request("GET", f"/markets{params}")
        return response.get("markets", [])

    def get_series(self, series_ticker: str) -> Dict:
        """
        Fetch series information by series ticker.

        Args:
            series_ticker: Series ticker (e.g., "KXHIGHNY" for NYC high temperature)

        Returns:
            Series object with metadata
        """
        response = self._request("GET", f"/series/{series_ticker}")
        return response.get("series", {})

    def get_market(self, ticker: str) -> Dict:
        """
        Fetch specific market by ticker.

        Args:
            ticker: Market ticker (e.g., "TEMPUSNYC20JUN-H")

        Returns:
            Market object with current price and volume
        """
        response = self._request("GET", f"/markets/{ticker}")
        return response.get("market", {})

    def get_orderbook(self, ticker: str) -> Dict:
        """
        Fetch orderbook for a specific market.

        Args:
            ticker: Market ticker

        Returns:
            Orderbook with yes_dollars and no_dollars bids
        """
        response = self._request("GET", f"/markets/{ticker}/orderbook")
        return response.get("orderbook_fp", {})

    def get_orderbooks(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Fetch orderbooks for multiple markets.

        Args:
            tickers: List of market tickers

        Returns:
            Dict mapping ticker → orderbook
        """
        data = {"tickers": tickers}
        response = self._request("POST", "/markets/orderbooks", data)
        return response.get("orderbooks", {})

    def search_markets(self, search_term: str) -> List[Dict]:
        """
        Search for markets by ticker/name containing search term.

        Args:
            search_term: Search string (e.g., "TEMP", "NYC")

        Returns:
            List of matching markets
        """
        # Search across all statuses to find markets
        all_markets = []
        for status in ["open", "unopened", "closed", "settled"]:
            markets = self.get_markets(status=status)
            logger.debug(f"Found {len(markets)} markets with status={status}")
            all_markets.extend(markets)

        logger.debug(f"Total markets across all statuses: {len(all_markets)}")

        matched = [
            m for m in all_markets
            if search_term.lower() in m.get("ticker", "").lower()
            or search_term.lower() in m.get("title", "").lower()
        ]

        logger.debug(f"Markets matching '{search_term}': {len(matched)}")
        if len(all_markets) > 0 and len(matched) == 0:
            # Show first market to understand structure
            logger.debug(f"Sample market structure: {all_markets[0]}")

        return matched

    def get_temperature_markets(self, city_name: str) -> List[Dict]:
        """
        Find all temperature markets for a specific city.

        Args:
            city_name: City name (e.g., "NYC", "New York")

        Returns:
            List of matching temperature markets
        """
        search_terms = [city_name, city_name[:3].upper()]
        markets = []

        for term in search_terms:
            found = self.search_markets(term)
            for market in found:
                # Filter to temperature-related markets
                title = market.get("title", "").upper()
                if any(keyword in title for keyword in ["TEMP", "HIGH", "LOW", "TEMPERATURE"]):
                    if market not in markets:
                        markets.append(market)

        return markets

    def estimate_market_probability(self, orderbook: Dict) -> float:
        """
        Estimate market-implied probability from orderbook.

        For binary markets, uses the mid-price between best yes and no bids.

        Args:
            orderbook: Orderbook with yes_dollars and no_dollars

        Returns:
            Estimated probability (0.0-1.0)
        """
        yes_bids = orderbook.get("yes_dollars", [])
        no_bids = orderbook.get("no_dollars", [])

        if not yes_bids or not no_bids:
            return 0.5  # No data, return neutral

        # Best (last) bid on each side
        best_yes = float(yes_bids[-1][0]) if yes_bids else 0.5
        best_no = float(no_bids[-1][0]) if no_bids else 0.5

        # Implied probability (YES probability)
        # YES price + NO price ≈ $1.00 in binary markets
        total = best_yes + best_no
        if total > 0:
            prob = best_yes / total
        else:
            prob = 0.5

        return max(0.0, min(1.0, prob))

    def get_portfolio_balance(self) -> Dict:
        """
        Get current portfolio balance and positions.

        Returns:
            Portfolio object with balance (in cents), balance_dollars, portfolio_value
        """
        response = self._request("GET", "/portfolio/balance")
        # Response has keys: balance, balance_dollars, balance_breakdown, portfolio_value, updated_ts
        return response

    def get_positions(self) -> List[Dict]:
        """
        Get current market positions.

        Returns:
            List of position objects (combines market_positions and event_positions)
        """
        response = self._request("GET", "/portfolio/positions")
        # Response has keys: cursor, market_positions, event_positions
        market_pos = response.get("market_positions", [])
        event_pos = response.get("event_positions", [])
        return market_pos + event_pos

    def get_account(self) -> Dict:
        """
        Get account information including limits and status.

        Returns:
            Account object with limits, balance, and metadata
        """
        response = self._request("GET", "/account")
        return response.get("account", {})

    def place_order(
        self,
        ticker: str,
        action: str,
        side: str,
        type_: str,
        count: int,
        price: Optional[int] = None,
        client_order_id: Optional[str] = None,
        time_in_force: str = "day",
        expiration_ts: Optional[int] = None
    ) -> Dict:
        """
        Place an order on the market.

        Args:
            ticker: Market ticker (e.g., "KXHIGHNY-26MAY21-T75")
            action: "buy" or "sell"
            side: "yes" or "no"
            type_: "limit" or "market"
            count: Number of contracts
            price: Price in cents (1-99) for limit orders
            client_order_id: UUID string for idempotency (max 64 chars)
            time_in_force: "day", "good_till_canceled", etc.
            expiration_ts: Unix timestamp for GTD orders

        Returns:
            Order object with order_id, status, created_ts_ms, leaves_qty
        """
        data = {
            "ticker": ticker,
            "action": action,
            "side": side,
            "type": type_,
            "count": count,
            "time_in_force": time_in_force,
        }

        if price is not None:
            # Determine which price field based on side
            if side == "yes":
                data["yes_price"] = price
            else:
                data["no_price"] = price

        if client_order_id:
            data["client_order_id"] = client_order_id

        if expiration_ts is not None:
            data["expiration_ts"] = expiration_ts

        response = self._request("POST", "/portfolio/orders", data)
        return response.get("order", {})

    def get_order(self, order_id: str) -> Dict:
        """
        Get status of a specific order.

        Args:
            order_id: Order identifier

        Returns:
            Order object with current status
        """
        response = self._request("GET", f"/portfolio/orders/{order_id}")
        return response.get("order", {})

    def list_orders(self, status: Optional[str] = None) -> List[Dict]:
        """
        List all orders with optional status filter.

        Args:
            status: Filter by status (resting, filled, canceled, etc.)

        Returns:
            List of order objects
        """
        endpoint = "/portfolio/orders"
        if status:
            endpoint += f"?status={status}"
        response = self._request("GET", endpoint)
        return response.get("orders", [])

    def cancel_order(self, order_id: str) -> Dict:
        """
        Cancel a specific order.

        Args:
            order_id: Order identifier

        Returns:
            Canceled order object
        """
        response = self._request("DELETE", f"/portfolio/orders/{order_id}")
        return response.get("order", {})

    def cancel_all_orders(self) -> bool:
        """
        Cancel all open orders.

        Returns:
            True if successful
        """
        response = self._request("DELETE", "/portfolio/orders")
        return bool(response)

    def amend_order(
        self,
        order_id: str,
        count: Optional[int] = None,
        price: Optional[int] = None
    ) -> Dict:
        """
        Amend an existing order.

        Args:
            order_id: Order identifier
            count: New order count (quantity)
            price: New price in cents

        Returns:
            Updated order object
        """
        data = {}
        if count is not None:
            data["count"] = count
        if price is not None:
            data["yes_price" if price else "no_price"] = price

        response = self._request("PUT", f"/portfolio/orders/{order_id}", data)
        return response.get("order", {})

    def get_fills(self, ticker: Optional[str] = None) -> List[Dict]:
        """
        Get all fills (executed trades).

        Args:
            ticker: Optional ticker filter

        Returns:
            List of fill objects with order_id, price, quantity, side
        """
        endpoint = "/portfolio/fills"
        if ticker:
            endpoint += f"?ticker={ticker}"
        response = self._request("GET", endpoint)
        return response.get("fills", [])

    def get_settlements(self) -> List[Dict]:
        """
        Get settlement outcomes and PnL for resolved markets.

        Returns:
            List of settlement objects with resolution outcomes and PnL
        """
        response = self._request("GET", "/portfolio/settlements")
        return response.get("settlements", [])

    def batch_orders(self, orders: List[Dict]) -> List[Dict]:
        """
        Place multiple orders in a single batch.

        Args:
            orders: List of order objects (each with ticker, action, side, etc.)

        Returns:
            List of placed order objects
        """
        data = {"orders": orders}
        response = self._request("POST", "/portfolio/events/orders/batched", data)
        return response.get("orders", [])


def test_connection(api_key_id: str, private_key_pem: str):
    """Test API connection and authentication."""
    client = KalshiAPIClient(api_key_id, private_key_pem)

    try:
        # Test portfolio endpoint
        portfolio = client.get_portfolio_balance()
        if portfolio:
            print("✓ API authentication successful")
            print(f"  Balance: ${portfolio.get('balance', 0) / 100:.2f}")
            return True
        else:
            print("✗ API authentication failed")
            return False
    except Exception as e:
        print(f"✗ API connection error: {e}")
        return False
