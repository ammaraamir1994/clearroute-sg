"""
Haze-Safe Singapore - ClearRoute SG FastAPI Application
Exposes REST endpoints for:
- Live NEA air quality & meteorological map data (PM2.5, PSI, Wind, Rainfall, Temperature across 5 SG regions)
- Historical Haze Scenario Simulator ('live', 'severe_2015', 'east_plume_2023', 'morning_inversion')
- "Should I go outside now?" personalized decision layer with custom duration, sensitivity, & inhaled dose (µg)
- Distance-aware cleanest nearby places + indoor air-filtered active refuges
- Gazetteer-backed journey planner comparing distance-accurate MRT, Bus, and Active Outdoor routes
- Heat-vs-Haze aware Clean Air Window forecasting
"""
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.models import (
    NEA_REGIONS,
    SG_GAZETTEER,
    HAZE_SCENARIOS,
    ACTIVITY_FACTORS,
    get_pm25_band
)
from backend.nea_service import fetch_realtime_nea, get_forecast_profile, find_clean_air_window
from backend.decision_engine import (
    build_decision_card,
    rank_clean_places,
    calculate_route_alternatives
)

SGT = timezone(timedelta(hours=8))

app = FastAPI(
    title="ClearRoute SG - Haze-Safe Singapore Decision Layer",
    description="Actionable location and timing choices turning official NEA PM2.5 & meteorological observations into clear personal decisions.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the single page web application
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
async def root():
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "ClearRoute SG API v2.0 is running. Access /api/air-quality or /docs"}


@app.get("/api/locations")
async def get_locations():
    """
    Returns the 40+ Singapore MRT hubs, neighborhoods, and landmarks in the Gazetteer
    plus available Haze Scenarios for UI autocomplete and simulation.
    """
    return {
        "locations": SG_GAZETTEER,
        "scenarios": [
            {"id": k, "name": v["name"], "badge": v["badge"], "description": v["description"]}
            for k, v in HAZE_SCENARIOS.items()
        ]
    }


@app.get("/api/air-quality")
async def get_air_quality(
    scenario: str = Query("live", description="Scenario: live, severe_2015, east_plume_2023, morning_inversion")
):
    """
    Returns Singapore 5-region PM2.5, PSI, and live meteorological data (Wind, Rainfall, Temp)
    with regional coordinates and official NEA bands.
    """
    nea_data = await fetch_realtime_nea(scenario=scenario)
    pm25_readings = nea_data["pm25"]
    psi_readings = nea_data["psi"]

    regions_output = []
    for reg_key, meta in NEA_REGIONS.items():
        pm25_val = float(pm25_readings.get(reg_key, 50.0))
        psi_val = float(psi_readings.get(reg_key, 60.0))
        band = get_pm25_band(pm25_val)

        regions_output.append({
            "region": reg_key,
            "name": meta["name"],
            "lat": meta["lat"],
            "lon": meta["lon"],
            "description": meta["description"],
            "pm25_1hr": pm25_val,
            "psi_24hr": psi_val,
            "band": band
        })

    return {
        "timestamp": nea_data.get("timestamp"),
        "is_live": nea_data.get("is_live", False),
        "is_simulation": nea_data.get("is_simulation", False),
        "scenario": nea_data.get("scenario", "live"),
        "scenario_meta": nea_data.get("scenario_meta"),
        "weather": nea_data.get("weather"),
        "source": "National Environment Agency (NEA) via data.gov.sg",
        "regions": regions_output
    }


@app.get("/api/decision")
async def get_decision(
    activity: str = Query("run", description="Activity key: run, walk, cycle, commute, sports, kids, park"),
    region: str = Query("central", description="Region: central, east, north, south, west"),
    duration_mins: Optional[int] = Query(None, description="Custom outdoor duration in minutes (5 to 240)"),
    sensitivity: str = Query("standard", description="Sensitivity profile: standard or sensitive"),
    scenario: str = Query("live", description="Scenario: live, severe_2015, east_plume_2023, morning_inversion")
):
    """
    Core 'Should I go outside now?' decision endpoint.
    Converts air & weather readings into Go / Delay / Indoor Alternative with inhaled dose (µg) & N95 guidance.
    """
    nea_data = await fetch_realtime_nea(scenario=scenario)
    decision = build_decision_card(
        activity_key=activity,
        region_key=region,
        pm25_data=nea_data["pm25"],
        duration_mins=duration_mins,
        sensitivity=sensitivity,
        weather=nea_data.get("weather")
    )
    return decision


@app.get("/api/clean-places")
async def get_clean_places(
    region: str = Query("central", description="User's current region"),
    category: str = Query("all", description="Filter: all, park, nature, outdoor, indoor"),
    duration_mins: int = Query(45, description="Planned visit duration in minutes"),
    scenario: str = Query("live", description="Scenario: live, severe_2015, east_plume_2023, morning_inversion")
):
    """
    Ranks Singapore outdoor parks and indoor air-filtered alternatives based on regional PM2.5
    and distance from the user's region.
    """
    nea_data = await fetch_realtime_nea(scenario=scenario)
    places = rank_clean_places(region, nea_data["pm25"], category, duration_mins=duration_mins)
    return {
        "user_region": region,
        "places": places,
        "advice": "Ranked by effective PM2.5 exposure and distance from your current region. Includes HEPA/AC indoor refuges when haze is elevated."
    }


@app.get("/api/route-planner")
async def plan_route(
    origin: str = Query("Tampines", description="Starting landmark, MRT station, or neighborhood"),
    destination: str = Query("Marina Bay", description="Destination landmark, MRT station, or neighborhood"),
    origin_region: Optional[str] = Query(None, description="Optional override for Origin NEA region"),
    dest_region: Optional[str] = Query(None, description="Optional override for Destination NEA region"),
    scenario: str = Query("live", description="Scenario: live, severe_2015, east_plume_2023, morning_inversion")
):
    """
    Computes distance-accurate, shelter-aware journey choices comparing MRT, Bus, and Active Outdoor modes.
    Automatically detects region and coordinates for 40+ Singapore locations.
    """
    nea_data = await fetch_realtime_nea(scenario=scenario)
    route_plan = calculate_route_alternatives(
        origin=origin,
        destination=destination,
        origin_region=origin_region,
        dest_region=dest_region,
        pm25_data=nea_data["pm25"],
        weather=nea_data.get("weather")
    )
    return route_plan


@app.get("/api/clean-window")
async def get_clean_air_window(
    region: str = Query("central", description="Region key"),
    activity: str = Query("run", description="Activity key for heat-vs-haze awareness"),
    scenario: str = Query("live", description="Scenario: live, severe_2015, east_plume_2023, morning_inversion")
):
    """
    Calculates the Clean Air Window (lowest-pollution & thermally safe forecasted time window today)
    using diurnal dispersion, live rainfall/wind modifiers, and equatorial heat-stress modeling.
    """
    nea_data = await fetch_realtime_nea(scenario=scenario)
    pm25_val = float(nea_data["pm25"].get(region.lower(), 65.0))
    now_h = datetime.now(SGT).hour
    forecast = get_forecast_profile(pm25_val, now_h, weather=nea_data.get("weather"))
    window = find_clean_air_window(forecast, activity_key=activity)
    return {
        "region": region,
        "current_pm25": pm25_val,
        "weather": nea_data.get("weather"),
        "window": window,
        "forecast_12hr": forecast
    }
