import config

def build_portfolio(forecast, bin_prices):
    """
    Build 3-bin portfolio based on forecast consensus.
    Returns list of bins to bet on, or None if invalid.
    """
    if not forecast["agree"]:
        return None

    icon = forecast["icon"]
    gfs = forecast["gfs"]
    ecmwf = forecast["ecmwf"]

    # Find closest pair of models
    distances = {
        ("icon", "gfs"): abs(icon - gfs),
        ("icon", "ecmwf"): abs(icon - ecmwf),
        ("gfs", "ecmwf"): abs(gfs - ecmwf),
    }
    closest_pair = min(distances, key=distances.get)
    closest_dist = distances[closest_pair]

    # Determine center and outlier
    if closest_dist <= 1.0:
        # Tight pair: use their avg as center, 3rd is outlier
        pair_temps = [
            icon if "icon" in closest_pair else None,
            gfs if "gfs" in closest_pair else None,
            ecmwf if "ecmwf" in closest_pair else None,
        ]
        pair_temps = [t for t in pair_temps if t is not None]
        center = sum(pair_temps) / len(pair_temps)
        outlier_temps = [icon, gfs, ecmwf]
        for t in pair_temps:
            outlier_temps.remove(t)
        outlier = outlier_temps[0] if outlier_temps else None
    else:
        # All three spread out: center = avg of all
        center = (icon + gfs + ecmwf) / 3
        outlier = None

    # Apply city bias (if applicable from context)
    # Note: caller should apply this before calling build_portfolio
    # or we'd need the city name here. For now, center as-is.

    # Find center bin
    center_bin = find_bin_for_temp(bin_prices, center)
    if center_bin is None:
        return None

    # Find adjacent bins
    above_1 = adjacent_bin(bin_prices, center_bin, "above")
    above_2 = adjacent_bin(bin_prices, above_1, "above") if above_1 else None
    below_1 = adjacent_bin(bin_prices, center_bin, "below")

    # Build plan based on outlier position
    if outlier is not None and outlier > center:
        # CASE A: outlier above center
        plan = [center_bin, above_1, above_2]
    else:
        # CASE B/C: outlier below or None
        plan = [center_bin, above_1, below_1]

    # Filter out None
    plan = [b for b in plan if b is not None]

    if len(plan) < 2:
        return None

    return plan


def find_bin_for_temp(bin_prices, temp_c):
    """
    Find bin whose range contains temp_c.
    If temp falls in a gap, return the nearest bin.
    """
    for b in bin_prices:
        if b["bin_low"] <= temp_c <= b["bin_high"]:
            return b

    # Fallback: find nearest bin midpoint
    closest_bin = None
    min_dist = float("inf")
    for b in bin_prices:
        mid = (b["bin_low"] + b["bin_high"]) / 2
        dist = abs(temp_c - mid)
        if dist < min_dist:
            min_dist = dist
            closest_bin = b

    return closest_bin


def adjacent_bin(bin_prices, bin_ref, direction):
    """
    Find adjacent bin in given direction (above/below).
    """
    if direction == "above":
        candidates = [b for b in bin_prices if b["bin_low"] > bin_ref["bin_high"]]
        return min(candidates, key=lambda b: b["bin_low"]) if candidates else None
    else:  # below
        candidates = [b for b in bin_prices if b["bin_high"] < bin_ref["bin_low"]]
        return max(candidates, key=lambda b: b["bin_high"]) if candidates else None


def passes_filters(plan):
    """
    Check if plan passes price filters.
    """
    if not plan:
        return False

    prices = [b["yes_price"] for b in plan]

    # No math edge: sum > 0.95
    if sum(prices) > 0.95:
        return False

    # Resolved bin: any < 0.01
    if any(p < 0.01 for p in prices):
        return False

    # Overpriced: any > 0.45
    if any(p > 0.45 for p in prices):
        return False

    return True


if __name__ == "__main__":
    # Test with mock data
    forecast = {
        "icon": 20.5,
        "gfs": 20.8,
        "ecmwf": 19.9,
        "spread": 0.9,
        "agree": True
    }

    bin_prices = [
        {"bin_low": 18, "bin_high": 19, "yes_price": 0.30, "market_id": "1"},
        {"bin_low": 19, "bin_high": 20, "yes_price": 0.25, "market_id": "2"},
        {"bin_low": 20, "bin_high": 21, "yes_price": 0.20, "market_id": "3"},
        {"bin_low": 21, "bin_high": 22, "yes_price": 0.15, "market_id": "4"},
    ]

    portfolio = build_portfolio(forecast, bin_prices)
    print(f"Portfolio: {portfolio}")
    print(f"Passes filters: {passes_filters(portfolio) if portfolio else False}")
