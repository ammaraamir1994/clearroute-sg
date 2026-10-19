"""
Haze-Safe Singapore - Real-Time NEA Data & Multi-Factor Forecasting Service
Fetches live 1-hr PM2.5, 24-hr PSI, and meteorological observations (Rainfall, Wind, Temperature, Humidity)
from official NEA / data.gov.sg APIs.
Includes historical haze scenario simulation and Heat-vs-Haze aware Clean Air Window modeling.
"""
import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import httpx

from backend.models import NEA_REGIONS, HAZE_SCENARIOS, ACTIVITY_FACTORS, get_pm25_band

logger = logging.getLogger("nea_service")

# SG Timezone UTC+8
SGT = timezone(timedelta(hours=8))

# Cache holder for live NEA data
_CACHE: Dict[str, Any] = {
    "last_fetched": 0,
    "pm25": None,
    "psi": None,
    "weather": None,
    "is_live": False,
    "timestamp": None
}
CACHE_TTL = 300  # 5 minutes

FALLBACK_MOCK_PM25 = {
    "central": 68.0,
    "east": 84.0,
    "north": 42.0,
    "south": 62.0,
    "west": 54.0
}

FALLBACK_MOCK_PSI = {
    "central": 88.0,
    "east": 104.0,
    "north": 64.0,
    "south": 82.0,
    "west": 75.0
}

DEFAULT_WEATHER = {
    "temp_c": 29.8,
    "humidity_pct": 76.0,
    "wind_speed_kmh": 10.5,
    "wind_direction": "SE",
    "rainfall_mm": 0.0,
    "condition": "Partly Cloudy • Coastal Breeze"
}


def _deg_to_cardinal(deg: float) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((deg + 22.5) // 45) % 8
    return dirs[idx]


async def _fetch_json(client: httpx.AsyncClient, url: str) -> Optional[Dict[str, Any]]:
    try:
        resp = await client.get(url)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.debug(f"Sub-request to {url} failed: {e}")
    return None


async def fetch_realtime_nea(scenario: str = "live") -> Dict[str, Any]:
    """
    Fetch 1-hr PM2.5, 24-hr PSI, and live meteorological indicators from data.gov.sg.
    If `scenario` is set to a historical simulation key ('severe_2015', 'east_plume_2023', 'morning_inversion'),
    returns that curated scenario so users and NEA reviewers can evaluate crisis behavior on clear days.
    """
    scenario_key = (scenario or "live").lower().strip()
    now_sgt = datetime.now(SGT)
    timestamp_str = now_sgt.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    # 1. Check if a historical / demo scenario is requested
    if scenario_key != "live" and scenario_key in HAZE_SCENARIOS:
        scen = HAZE_SCENARIOS[scenario_key]
        return {
            "scenario": scenario_key,
            "scenario_meta": {
                "id": scen["id"],
                "name": scen["name"],
                "badge": scen["badge"],
                "description": scen["description"]
            },
            "pm25": dict(scen["pm25"]),
            "psi": dict(scen["psi"]),
            "weather": dict(scen.get("weather", DEFAULT_WEATHER)),
            "is_live": False,
            "is_simulation": True,
            "timestamp": timestamp_str
        }

    # 2. Live NEA mode with 5-minute TTL cache
    now = time.time()
    if _CACHE["pm25"] and (now - _CACHE["last_fetched"]) < CACHE_TTL:
        return {
            "scenario": "live",
            "scenario_meta": HAZE_SCENARIOS["live"],
            "pm25": _CACHE["pm25"],
            "psi": _CACHE["psi"],
            "weather": _CACHE["weather"] or DEFAULT_WEATHER,
            "is_live": _CACHE["is_live"],
            "is_simulation": False,
            "cached": True,
            "timestamp": _CACHE.get("timestamp", timestamp_str)
        }

    pm25_readings: Dict[str, float] = {}
    psi_readings: Dict[str, float] = {}
    weather_data = dict(DEFAULT_WEATHER)
    source_live = False

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            pm25_res, psi_res, temp_res, rain_res, wind_spd_res, wind_dir_res = await asyncio.gather(
                _fetch_json(client, "https://api.data.gov.sg/v1/environment/pm25"),
                _fetch_json(client, "https://api.data.gov.sg/v1/environment/psi"),
                _fetch_json(client, "https://api.data.gov.sg/v1/environment/air-temperature"),
                _fetch_json(client, "https://api.data.gov.sg/v1/environment/rainfall"),
                _fetch_json(client, "https://api.data.gov.sg/v1/environment/wind-speed"),
                _fetch_json(client, "https://api.data.gov.sg/v1/environment/wind-direction"),
            )

            if pm25_res and pm25_res.get("items"):
                latest = pm25_res["items"][0]
                timestamp_str = latest.get("timestamp", timestamp_str)
                raw_pm = latest.get("readings", {}).get("pm25_one_hourly", {})
                if raw_pm:
                    pm25_readings = {k: float(v) for k, v in raw_pm.items() if k in NEA_REGIONS}
                    source_live = True

            if psi_res and psi_res.get("items"):
                latest_psi = psi_res["items"][0]
                raw_psi = latest_psi.get("readings", {}).get("psi_twenty_four_hourly", {})
                if raw_psi:
                    psi_readings = {k: float(v) for k, v in raw_psi.items() if k in NEA_REGIONS}

            # Parse Air Temperature (°C)
            if temp_res and temp_res.get("items"):
                readings = temp_res["items"][0].get("readings", [])
                vals = [float(r["value"]) for r in readings if "value" in r]
                if vals:
                    weather_data["temp_c"] = round(sum(vals) / len(vals), 1)

            # Parse Rainfall (mm in last interval)
            if rain_res and rain_res.get("items"):
                readings = rain_res["items"][0].get("readings", [])
                vals = [float(r["value"]) for r in readings if "value" in r]
                if vals:
                    # Average rainfall across active stations or max shower intensity
                    avg_rain = sum(vals) / len(vals)
                    max_rain = max(vals)
                    weather_data["rainfall_mm"] = round(max_rain if max_rain > 1.0 else avg_rain, 1)

            # Parse Wind Speed (knots -> km/h, 1 knot = 1.852 km/h)
            if wind_spd_res and wind_spd_res.get("items"):
                readings = wind_spd_res["items"][0].get("readings", [])
                vals = [float(r["value"]) for r in readings if "value" in r]
                if vals:
                    avg_knots = sum(vals) / len(vals)
                    weather_data["wind_speed_kmh"] = round(avg_knots * 1.852, 1)

            # Parse Wind Direction (degrees -> cardinal)
            if wind_dir_res and wind_dir_res.get("items"):
                readings = wind_dir_res["items"][0].get("readings", [])
                vals = [float(r["value"]) for r in readings if "value" in r]
                if vals:
                    avg_deg = sum(vals) / len(vals)
                    weather_data["wind_direction"] = _deg_to_cardinal(avg_deg)

            # Describe condition based on live weather
            if weather_data["rainfall_mm"] >= 2.0:
                weather_data["condition"] = f"Rain Washout Active ({weather_data['rainfall_mm']} mm) • Wet Deposition Clearing PM2.5"
            elif weather_data["wind_speed_kmh"] >= 15.0:
                weather_data["condition"] = f"Breezy {weather_data['wind_direction']} Winds ({weather_data['wind_speed_kmh']} km/h) • Good Dispersion"
            else:
                weather_data["condition"] = f"{weather_data['temp_c']}°C • {weather_data['wind_direction']} Breeze ({weather_data['wind_speed_kmh']} km/h)"

    except Exception as exc:
        logger.warning(f"Could not reach data.gov.sg live endpoint: {exc}. Using fallback snapshot.")

    if not pm25_readings:
        pm25_readings = dict(FALLBACK_MOCK_PM25)
        psi_readings = dict(FALLBACK_MOCK_PSI)
        source_live = False

    # Update cache
    _CACHE["pm25"] = pm25_readings
    _CACHE["psi"] = psi_readings
    _CACHE["weather"] = weather_data
    _CACHE["is_live"] = source_live
    _CACHE["last_fetched"] = now
    _CACHE["timestamp"] = timestamp_str

    # Persist observation snapshot to SQLite if live
    try:
        from backend.storage import record_observations
        record_observations(timestamp_str, pm25_readings, psi_readings)
    except Exception as e:
        logger.debug(f"Observation persistence notice: {e}")

    return {
        "scenario": "live",
        "scenario_meta": HAZE_SCENARIOS["live"],
        "pm25": pm25_readings,
        "psi": psi_readings,
        "weather": weather_data,
        "is_live": source_live,
        "is_simulation": False,
        "timestamp": timestamp_str
    }


def get_forecast_profile(
    base_pm25: float,
    current_hour: int,
    weather: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Multi-factor Singapore particulate & thermal comfort projection:
    1. Boundary Layer & Sea Breeze Diurnal Curve:
       Morning inversion trap (08:00-11:00) keeps particulates elevated;
       Afternoon convective mixing (13:00-17:00) lowers concentration.
    2. Meteorological Modifiers:
       - Rainfall wet deposition (rain >= 1.0 mm accelerates particulate washout by 15-25%)
       - Wind speed dispersion (winds >= 14 km/h reduce stagnation)
    3. Equatorial Heat Stress Curve:
       Tracks hourly temperature & thermal load so outdoor runners aren't sent into 33°C midday sun
       when morning air is already clean.
    """
    w = weather or DEFAULT_WEATHER
    rainfall = float(w.get("rainfall_mm", 0.0))
    wind_kmh = float(w.get("wind_speed_kmh", 10.0))
    base_temp = float(w.get("temp_c", 29.5))

    # Standard diurnal relative PM2.5 factor (hours 0 to 23)
    diurnal_curve = [
        0.85, 0.82, 0.80, 0.78, 0.82, 0.88, 0.98, 1.10,  # 00:00 - 07:00
        1.20, 1.24, 1.16, 1.04, 0.88, 0.76, 0.71, 0.69,  # 08:00 - 15:00
        0.72, 0.78, 0.88, 0.98, 1.06, 1.02, 0.94, 0.88   # 16:00 - 23:00
    ]

    # Singapore typical diurnal temperature offset (°C relative to daily mean)
    temp_offsets = [
        -2.2, -2.4, -2.6, -2.8, -2.8, -2.6, -2.2, -1.2,  # 00:00 - 07:00
        +0.2, +1.4, +2.3, +3.0, +3.4, +3.5, +3.2, +2.6,  # 08:00 - 15:00
        +1.8, +0.9, +0.0, -0.7, -1.2, -1.6, -1.9, -2.1   # 16:00 - 23:00
    ]

    current_factor = diurnal_curve[current_hour % 24]
    current_temp_offset = temp_offsets[current_hour % 24]
    est_daily_mean_temp = max(26.0, min(31.5, base_temp - current_temp_offset))

    forecast = []
    for i in range(12):  # Next 12 hours
        h = (current_hour + i) % 24
        target_factor = diurnal_curve[h]

        # Apply meteorological modifiers for future hours (i > 0)
        meteo_multiplier = 1.0
        if i > 0:
            if rainfall >= 2.0 and i <= 4:
                # Active wet deposition washes out fine particulates over next few hours
                meteo_multiplier *= 0.82
            elif rainfall >= 0.5 and i <= 3:
                meteo_multiplier *= 0.90

            if wind_kmh >= 15.0:
                meteo_multiplier *= 0.92

        projected_pm25 = max(8.0, base_pm25 * (target_factor / current_factor) * meteo_multiplier)
        band = get_pm25_band(projected_pm25)

        hr_temp = round(est_daily_mean_temp + temp_offsets[h], 1)
        is_peak_heat = 11 <= h <= 15 and hr_temp >= 31.0

        forecast.append({
            "hour_offset": i,
            "hour": h,
            "time_label": f"{h:02d}:00",
            "pm25": round(projected_pm25, 1),
            "temp_c": hr_temp,
            "heat_stress": "HIGH_HEAT" if is_peak_heat else ("WARM" if 10 <= h <= 17 else "COOL"),
            "band": band
        })

    return forecast


def find_clean_air_window(
    forecast: List[Dict[str, Any]],
    activity_key: str = "run"
) -> Dict[str, Any]:
    """
    Identifies the optimal 2-hour outdoor window in the upcoming 12-hour forecast.
    Crucial Real-World Improvement (Heat vs. Haze Trade-Off):
    - When air is ALREADY clean (PM2.5 <= 35 µg/m³), do NOT advise runners/cyclists to wait until 2:00 PM
      (peak equatorial UV & heat stress) just to save 3 µg/m³!
    - When air is Elevated/High (> 55 µg/m³), prioritize particulate reduction while flagging heat conditions.
    """
    if not forecast or len(forecast) < 2:
        return {
            "best_window": "Now",
            "best_start_hour": 0,
            "best_pm25_avg": 0,
            "now_pm25": 0,
            "reduction_pct": 0,
            "heat_note": "Normal thermal conditions",
            "recommendation": "Current window is suitable."
        }

    act = ACTIVITY_FACTORS.get(activity_key, ACTIVITY_FACTORS["walk"])
    heat_sensitive = act.get("heat_sensitive", False)
    now_pm25 = float(forecast[0]["pm25"])
    now_heat = forecast[0].get("heat_stress", "COOL")

    # Case A: Air is already very clean (<= 35 µg/m³, well within Normal Band I)
    if now_pm25 <= 35.0:
        # If it's currently cool/comfortable, right now is the best window!
        if not (heat_sensitive and now_heat == "HIGH_HEAT"):
            end_h = (forecast[1]["hour"] + 1) % 24
            window_str = f"Now ({forecast[0]['hour']:02d}:00 – {end_h:02d}:00)"
            return {
                "best_window": window_str,
                "best_start_hour": forecast[0]["hour"],
                "best_pm25_avg": round((forecast[0]["pm25"] + forecast[1]["pm25"]) / 2.0, 1),
                "now_pm25": now_pm25,
                "reduction_pct": 0,
                "heat_note": f"Comfortable temperature (~{forecast[0].get('temp_c', 28.5)}°C)",
                "recommendation": f"Air is already clean ({now_pm25:.0f} µg/m³). Go now rather than waiting for midday heat."
            }
        else:
            # Air is clean, but it's currently blazing midday heat (11 AM - 3 PM) and user wants to run/cycle
            # Find the first cooler late-afternoon/evening window (17:00+) where PM2.5 is still <= 45
            best_idx = 0
            for i in range(len(forecast) - 1):
                if forecast[i].get("heat_stress") != "HIGH_HEAT" and forecast[i]["pm25"] <= 45.0:
                    best_idx = i
                    break
            start_h = forecast[best_idx]["hour"]
            end_h = (forecast[best_idx + 1]["hour"] + 1) % 24
            window_str = f"{start_h:02d}:00 – {end_h:02d}:00"
            avg_pm = (forecast[best_idx]["pm25"] + forecast[best_idx + 1]["pm25"]) / 2.0
            return {
                "best_window": window_str,
                "best_start_hour": start_h,
                "best_pm25_avg": round(avg_pm, 1),
                "now_pm25": now_pm25,
                "reduction_pct": max(0, round(((now_pm25 - avg_pm) / max(1.0, now_pm25)) * 100)),
                "heat_note": "Avoids 11:00–15:00 equatorial heat stress while air stays Band I (Clean)",
                "recommendation": f"Air is clean now ({now_pm25:.0f} µg/m³), but midday heat is high. Best thermal + clean air window for {act['label'].lower()} is {window_str}."
            }

    # Case B: PM2.5 is > 35 µg/m³ (Moderate, Elevated, High, or Very High)
    # Score candidate 2-hour windows: primary weight on PM2.5, secondary penalty for HIGH_HEAT if strenuous activity
    best_score = float("inf")
    best_start_idx = 0
    best_avg = now_pm25

    for i in range(len(forecast) - 1):
        w_pm = (forecast[i]["pm25"] + forecast[i + 1]["pm25"]) / 2.0
        heat_penalty = 0.0
        if heat_sensitive and (forecast[i].get("heat_stress") == "HIGH_HEAT" or forecast[i + 1].get("heat_stress") == "HIGH_HEAT"):
            # Equivalent penalty of 10 ug/m3 for high midday heat during strenuous exercise
            heat_penalty = 10.0

        score = w_pm + heat_penalty
        if score < best_score:
            best_score = score
            best_avg = w_pm
            best_start_idx = i

    start_h = forecast[best_start_idx]["hour"]
    end_h = (forecast[best_start_idx + 1]["hour"] + 1) % 24

    diff = now_pm25 - best_avg
    reduction_pct = max(0, round((diff / max(1.0, now_pm25)) * 100))

    window_str = f"{start_h:02d}:00 – {end_h:02d}:00"
    heat_at_best = forecast[best_start_idx].get("heat_stress", "COOL")
    temp_at_best = forecast[best_start_idx].get("temp_c", 30.0)

    if heat_at_best == "HIGH_HEAT" and heat_sensitive:
        heat_note = f"Warm midday window (~{temp_at_best}°C) — hydrate well & seek shaded paths"
    else:
        heat_note = f"Favorable thermal & dispersion window (~{temp_at_best}°C)"

    if best_start_idx == 0 or reduction_pct < 5:
        recommendation_label = "Current window is already among the lowest-exposure periods today."
    else:
        recommendation_label = f"Shift outdoor plans to {window_str} for ~{reduction_pct}% lower PM2.5 exposure."

    return {
        "best_window": window_str,
        "best_start_hour": start_h,
        "best_pm25_avg": round(best_avg, 1),
        "now_pm25": now_pm25,
        "reduction_pct": reduction_pct,
        "heat_note": heat_note,
        "recommendation": recommendation_label
    }
