import re
from datetime import date

def scan_markets(markets_data, city, target_date):
    """
    Filter markets for a given city and date.
    Parse bin ranges from market titles.
    Returns list of {market_id, token_id, bin_low, bin_high, bin_mid, yes_price}.

    markets_data: list of market dicts from Polymarket CLOB API
    """
    results = []

    # Date pattern for matching (e.g., "May 1", "May 01")
    month_day = target_date.strftime("(%b %d|%B %d)")
    date_pattern = re.compile(month_day, re.IGNORECASE)

    # Bin pattern: "56-57°F" or "20-21°C"
    bin_pattern = re.compile(r"(\d+)-(\d+)°([FC])")

    for market in markets_data:
        title = market.get("question", "")

        # Check if city name and date are in title
        if city.lower() not in title.lower():
            continue
        if not date_pattern.search(title):
            continue

        # Extract bin range
        match = bin_pattern.search(title)
        if not match:
            continue

        bin_low = float(match.group(1))
        bin_high = float(match.group(2))
        unit = match.group(3)

        bin_mid = (bin_low + bin_high) / 2
        token_id = market.get("tokenId", "")
        market_id = market.get("id", "")
        yes_price = market.get("yes_price", market.get("price", 0.5))

        results.append({
            "market_id": market_id,
            "token_id": token_id,
            "bin_low": bin_low,
            "bin_high": bin_high,
            "bin_mid": bin_mid,
            "yes_price": yes_price,
            "unit": unit,
        })

    # Sort by bin_low
    results.sort(key=lambda x: x["bin_low"])
    return results


if __name__ == "__main__":
    # Test with mock market data
    mock_markets = [
        {
            "id": "market_1",
            "tokenId": "token_1",
            "question": "Will the high temperature in NYC on May 1 be between 56-57°F?",
            "yes_price": 0.30,
        },
        {
            "id": "market_2",
            "tokenId": "token_2",
            "question": "Will the high temperature in NYC on May 1 be between 57-58°F?",
            "yes_price": 0.25,
        },
        {
            "id": "market_3",
            "tokenId": "token_3",
            "question": "Will the high temperature in NYC on May 2 be between 56-57°F?",
            "yes_price": 0.20,
        },
    ]

    target_date = date(2026, 5, 1)
    results = scan_markets(mock_markets, "NYC", target_date)
    print(f"Found {len(results)} markets for NYC on {target_date}:")
    for r in results:
        print(f"  {r['bin_low']}-{r['bin_high']}°{r['unit']}: ${r['yes_price']:.2f}")
