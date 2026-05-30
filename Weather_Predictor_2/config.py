CITIES = {
    # US — resolves in °F
    "NYC":       {"lat": 40.7772, "lon": -73.8726, "station": "KLGA", "unit": "F"},
    "Atlanta":   {"lat": 33.6407, "lon": -84.4277, "station": "KATL", "unit": "F"},
    "Miami":     {"lat": 25.7959, "lon": -80.2870, "station": "KMIA", "unit": "F"},
    "Chicago":   {"lat": 41.9742, "lon": -87.9073, "station": "KORD", "unit": "F"},
    "Dallas":    {"lat": 32.8471, "lon": -96.8518, "station": "KDAL", "unit": "F"},
    # Asia — resolves in °C
    "Tokyo":     {"lat": 35.5494, "lon": 139.7798, "station": "RJTT", "unit": "C"},
    "HongKong":  {"lat": 22.3022, "lon": 114.1742, "station": "HKO",  "unit": "C"},
    "Singapore": {"lat":  1.3502, "lon": 103.9940, "station": "WSSS", "unit": "C"},
    "Seoul":     {"lat": 37.4691, "lon": 126.4505, "station": "RKSI", "unit": "C"},
    # Europe — resolves in °C
    "London":    {"lat": 51.5048, "lon":   0.0495, "station": "EGLC", "unit": "C"},
    "Paris":     {"lat": 48.9694, "lon":   2.4414, "station": "LFPB", "unit": "C"},
}

# Per-city forecast bias corrections (°C). Apply before bin selection.
CITY_BIAS_C = {
    "HongKong": +1.0,  # models run cold in subtropical summer
}

WIN_MIN_H = 18.0
WIN_MAX_H = 30.0
