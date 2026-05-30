import requests
from datetime import date

def fetch_forecast(lat, lon, target_date):
    """
    Fetch forecast from Open-Meteo for 3 models (ICON, GFS, ECMWF).
    Returns max temp for each model, spread, and agreement status.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "models": "icon_seamless,gfs_seamless,ecmwf_ifs025",
        "hourly": "temperature_2m",
        "bias_correction": "true",
        "temperature_unit": "celsius",
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    # Extract max temperature for each model
    hourly = data["hourly"]
    temps = hourly["temperature_2m"]

    # Models are in order: icon, gfs, ecmwf
    temps_by_model = {}
    for i, model_name in enumerate(["icon", "gfs", "ecmwf"]):
        model_temps = temps[i] if isinstance(temps, list) and len(temps) > i else []
        if model_temps:
            temps_by_model[model_name] = max(model_temps)
        else:
            temps_by_model[model_name] = None

    # Compute spread
    valid_temps = [t for t in temps_by_model.values() if t is not None]
    if not valid_temps:
        return {
            "icon": None, "gfs": None, "ecmwf": None,
            "spread": None, "agree": False
        }

    spread = max(valid_temps) - min(valid_temps)
    agree = spread <= 3.0

    return {
        "icon": temps_by_model["icon"],
        "gfs": temps_by_model["gfs"],
        "ecmwf": temps_by_model["ecmwf"],
        "spread": spread,
        "agree": agree
    }


if __name__ == "__main__":
    # Test: NYC tomorrow
    from datetime import date, timedelta
    tomorrow = date.today() + timedelta(days=1)

    result = fetch_forecast(40.7772, -73.8726, tomorrow)
    print(f"NYC {tomorrow}:")
    print(f"  ICON: {result['icon']:.1f}°C")
    print(f"  GFS:  {result['gfs']:.1f}°C")
    print(f"  ECMWF: {result['ecmwf']:.1f}°C")
    print(f"  Spread: {result['spread']:.1f}°C")
    print(f"  Agree: {result['agree']}")
