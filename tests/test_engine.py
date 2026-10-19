import pytest
from backend.models import (
    calculate_hes,
    calculate_inhaled_dose_ug,
    get_pm25_band,
    resolve_sg_location,
    haversine_km,
    NEA_REGIONS
)
from backend.decision_engine import (
    build_decision_card,
    rank_clean_places,
    calculate_route_alternatives
)
from backend.nea_service import (
    fetch_realtime_nea,
    get_forecast_profile,
    find_clean_air_window
)


def test_pm25_bands():
    assert get_pm25_band(25)["level"] == "LOWER"
    assert get_pm25_band(70)["level"] == "MODERATE"
    assert get_pm25_band(120)["level"] == "ELEVATED"
    assert get_pm25_band(180)["level"] == "HIGH"
    assert get_pm25_band(300)["level"] == "VERY_HIGH"


def test_calculate_hes_and_dosimetry():
    # 20 min walk (factor 1.5, 18 L/min) at 50 ug/m3 -> HES = 15.0
    hes_walk = calculate_hes(50.0, 20.0, "walk")
    assert hes_walk == 15.0
    dose_walk = calculate_inhaled_dose_ug(50.0, 20.0, "walk")
    # 50 ug/m3 * 0.018 m3/min * 20 min = 18.0 ug
    assert dose_walk["inhaled_ug"] == 18.0

    # 35 min run (factor 3.0, 52 L/min) at 100 ug/m3 -> HES = 105.0
    hes_run = calculate_hes(100.0, 35.0, "run")
    assert hes_run == 105.0
    dose_run = calculate_inhaled_dose_ug(100.0, 35.0, "run")
    # 100 * 0.052 * 35 = 182.0 ug
    assert dose_run["inhaled_ug"] == 182.0


def test_decision_card_duration_sensitivity_and_escapes():
    # East plume scenario where North/West are much cleaner than Central/East
    pm_data = {"central": 95.0, "east": 135.0, "north": 38.0, "south": 80.0, "west": 42.0}
    card_std = build_decision_card("walk", "central", pm_data, duration_mins=25, sensitivity="standard")
    card_sens = build_decision_card("walk", "central", pm_data, duration_mins=90, sensitivity="sensitive")

    # Standard 25m walk at 95 ug/m3 is GO/Acceptable, whereas 90m sensitive walk escalates to DELAY/AVOID
    assert card_std["status"] == "GO"
    assert card_sens["status"] in ("DELAY", "AVOID_OUTDOORS")
    assert card_sens["dosimetry"]["inhaled_ug"] > card_std["dosimetry"]["inhaled_ug"]

    # Should identify North region as a cleaner regional escape (95 - 38 = 57 ug/m3 cleaner)
    assert card_std["regional_escape"] is not None
    assert card_std["regional_escape"]["region"] == "north"
    assert "indoor_refuge" in card_std


def test_gazetteer_distance_accurate_route_planner():
    pm_data = {"central": 140.0, "east": 130.0, "west": 110.0}

    # Short central walk (Bugis to City Hall ~ 1.0 km) vs Cross-island commute (Tampines to Jurong East ~ 29 km)
    short_trip = calculate_route_alternatives("Bugis", "City Hall", pm25_data=pm_data)
    long_trip = calculate_route_alternatives("Tampines", "Jurong East", pm25_data=pm_data)

    assert short_trip["distance_km"] < 3.0
    assert long_trip["distance_km"] > 20.0
    assert long_trip["routes"][0]["total_min"] > short_trip["routes"][0]["total_min"]

    # Verify auto-detection of regions without manual region input
    assert long_trip["origin_region_key"] == "east"
    assert long_trip["dest_region_key"] == "west"

    # MRT route always achieves lower inhaled dose than 100% outdoor mode
    mrt = long_trip["routes"][0]
    outdoor = long_trip["routes"][2]
    assert mrt["id"] == "mrt_optimal"
    assert mrt["inhaled_ug"] < outdoor["inhaled_ug"]


def test_clean_places_distance_and_indoor_refuges():
    pm_data = {"central": 150.0, "east": 80.0, "north": 70.0, "south": 110.0, "west": 140.0}
    places_all = rank_clean_places("central", pm_data, category="all")
    places_indoor = rank_clean_places("central", pm_data, category="indoor")

    assert len(places_all) > 0
    assert len(places_indoor) >= 5
    # When central PM2.5 is 150, indoor filtered venues have much lower effective PM2.5 (~22-45 ug/m3)
    assert all(p["is_indoor"] for p in places_indoor)
    assert places_indoor[0]["pm25_1hr"] < 60.0
    assert "distance_km" in places_all[0]


def test_heat_vs_haze_clean_window():
    # When air is ALREADY clean (e.g. 18 ug/m3 at 8 AM), should NOT tell runner to wait for 2 PM heat!
    clean_morning_forecast = get_forecast_profile(18.0, current_hour=8, weather={"temp_c": 27.5, "rainfall_mm": 0.0, "wind_speed_kmh": 12.0})
    window_clean = find_clean_air_window(clean_morning_forecast, activity_key="run")
    assert "Now" in window_clean["best_window"]
    assert "already clean" in window_clean["recommendation"].lower()

    # When air is Elevated (e.g. 95 ug/m3 at 9 AM), should recommend shifting to afternoon dispersion window
    hazy_morning_forecast = get_forecast_profile(95.0, current_hour=9, weather={"temp_c": 29.0, "rainfall_mm": 2.5, "wind_speed_kmh": 16.0})
    window_hazy = find_clean_air_window(hazy_morning_forecast, activity_key="run")
    assert window_hazy["reduction_pct"] > 20


@pytest.mark.anyio
async def test_historical_scenarios():
    scen_2015 = await fetch_realtime_nea(scenario="severe_2015")
    assert scen_2015["is_simulation"] is True
    assert scen_2015["pm25"]["west"] > 200.0
