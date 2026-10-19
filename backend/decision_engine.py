"""
Haze-Safe Singapore - ClearRoute SG Decision Engine
Calculates:
1. "Should I go outside now?" personalized decision cards with custom duration, sensitivity, & inhaled dose (µg)
2. Distance-aware cleanest nearby places + HEPA/air-conditioned indoor active refuges
3. Gazetteer-backed, distance-accurate multi-modal journey planner (MRT vs. Bus vs. Active Outdoor)
4. Heat-vs-Haze aware Clean Air Window timing optimization
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from backend.models import (
    NEA_REGIONS,
    POPULAR_PLACES,
    INDOOR_ALTERNATIVES,
    ACTIVITY_FACTORS,
    get_pm25_band,
    calculate_hes,
    calculate_inhaled_dose_ug,
    get_protective_guidance,
    haversine_km,
    resolve_sg_location
)
from backend.nea_service import get_forecast_profile, find_clean_air_window

SGT = timezone(timedelta(hours=8))


def build_decision_card(
    activity_key: str,
    region_key: str,
    pm25_data: Dict[str, float],
    duration_mins: Optional[int] = None,
    sensitivity: str = "standard",
    weather: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate actionable decision recommendation for an activity in a given region.
    Incorporates custom duration, personal respiratory sensitivity, inhaled PM2.5 dose (µg),
    N95/indoor filtration guidance, and regional/indoor fallback options.
    """
    region = region_key.lower() if region_key.lower() in NEA_REGIONS else "central"
    act_info = ACTIVITY_FACTORS.get(activity_key, ACTIVITY_FACTORS["walk"])
    current_pm25 = float(pm25_data.get(region, 50.0))
    band = get_pm25_band(current_pm25)

    duration = int(duration_mins) if duration_mins and duration_mins > 0 else int(act_info["default_mins"])
    duration = max(5, min(240, duration))

    hes = calculate_hes(current_pm25, duration, activity_key)
    dosimetry = calculate_inhaled_dose_ug(current_pm25, duration, activity_key)
    protection = get_protective_guidance(current_pm25, activity_key, sensitivity, dosimetry["inhaled_ug"])

    # 12-hour multi-factor forecast & Heat-vs-Haze Clean Air Window
    now_hour = datetime.now(SGT).hour
    forecast = get_forecast_profile(current_pm25, now_hour, weather=weather)
    window_info = find_clean_air_window(forecast, activity_key=activity_key)

    # Check if another region in Singapore is significantly cleaner right now
    cleanest_reg = min(pm25_data.items(), key=lambda x: float(x[1])) if pm25_data else (region, current_pm25)
    cleanest_reg_key, cleanest_reg_pm = cleanest_reg[0], float(cleanest_reg[1])
    regional_escape = None
    if cleanest_reg_key != region and (current_pm25 - cleanest_reg_pm) >= 18.0:
        regional_escape = {
            "region": cleanest_reg_key,
            "region_name": NEA_REGIONS[cleanest_reg_key]["name"],
            "pm25_1hr": cleanest_reg_pm,
            "diff_ug": round(current_pm25 - cleanest_reg_pm, 0),
            "note": f"{NEA_REGIONS[cleanest_reg_key]['name']} Region is currently {current_pm25 - cleanest_reg_pm:.0f} µg/m³ cleaner ({cleanest_reg_pm:.0f} µg/m³)."
        }

    # Find best matching indoor refuge in or near user's region
    matching_indoors = [
        ind for ind in INDOOR_ALTERNATIVES
        if ind["region"] == region and activity_key in ind["suitable_for"]
    ] or [ind for ind in INDOOR_ALTERNATIVES if activity_key in ind["suitable_for"]] or INDOOR_ALTERNATIVES
    top_indoor = matching_indoors[0]
    indoor_eff_pm25 = round(current_pm25 * top_indoor["filtration_factor"], 1)

    # Decision Matrix accounting for PM2.5, Activity Ventilation, Duration, & Sensitivity
    level = band["level"]
    is_high_intensity = act_info["factor"] >= 2.0
    is_sensitive = (sensitivity == "sensitive") or (activity_key == "kids")
    is_long_duration = duration >= 60

    # Effective threshold shift for sensitive groups or long durations (>60 mins)
    effective_pm25 = current_pm25 * (1.25 if is_sensitive else 1.0) * (1.15 if is_long_duration else 1.0)

    if effective_pm25 <= 55:
        status = "GO"
        color = "#10b981"
        action = "🟢 Favorable conditions for outdoor activity"
        guidance = (
            f"Air quality in {NEA_REGIONS[region]['name']} is clean ({current_pm25:.0f} µg/m³). "
            f"A {duration}-min {act_info['label'].lower()} inhales ~{dosimetry['inhaled_ug']} µg of PM2.5 "
            f"(breathing at ~{dosimetry['ventilation_lpm']:.0f} L/min). {window_info['recommendation']}"
        )
    elif effective_pm25 <= 100:
        if is_high_intensity or is_sensitive:
            status = "MONITOR"
            color = "#f59e0b"
            action = f"🟡 Moderate particulate exposure ({current_pm25:.0f} µg/m³) — Pace effort"
            guidance = (
                f"At {act_info['factor']}x resting ventilation (~{dosimetry['ventilation_lpm']:.0f} L/min), "
                f"a {duration}-min session results in ~{dosimetry['inhaled_ug']} µg inhaled PM2.5. "
                f"{'Sensitive individuals should shorten duration or use an indoor venue. ' if is_sensitive else ''}"
                f"{window_info['recommendation']}"
            )
        else:
            status = "GO"
            color = "#10b981"
            action = "🟢 Acceptable for normal outdoor walking & commuting"
            guidance = (
                f"PM2.5 is {current_pm25:.0f} µg/m³. Standard {duration}-min {act_info['label'].lower()} "
                f"carries manageable exposure (~{dosimetry['inhaled_ug']} µg inhaled)."
            )
    elif effective_pm25 <= 150:
        if is_high_intensity or is_sensitive:
            status = "DELAY"
            color = "#f97316"
            action = f"🟠 Delay outdoor {act_info['label'].lower()} or switch indoors"
            guidance = (
                f"Elevated PM2.5 ({current_pm25:.0f} µg/m³) combined with {act_info['factor']}x exercise breathing rate "
                f"leads to ~{dosimetry['inhaled_ug']} µg inhaled particulates over {duration} mins. "
                f"{window_info['recommendation']} Or move indoors to {top_indoor['name']} (~{indoor_eff_pm25:.0f} µg/m³ effective)."
            )
        else:
            status = "REDUCE_EXPOSURE"
            color = "#f97316"
            action = "🟠 Minimize prolonged outdoor segments"
            guidance = (
                f"Take sheltered linkways or underground MRT connections. "
                f"Shortening outdoor time from {duration} mins to 15 mins cuts inhaled dose by "
                f"~{max(0, round((1 - 15 / max(15, duration)) * 100))}%."
            )
    else:  # HIGH or VERY_HIGH
        status = "AVOID_OUTDOORS"
        color = "#ef4444"
        action = f"🔴 High exposure right now — postpone outdoor {act_info['label'].lower()}"
        guidance = (
            f"Current 1-hr PM2.5 is {current_pm25:.0f} µg/m³ ({band['nea_band']}). "
            f"Doing {duration} mins of {act_info['label'].lower()} outdoors would inhale ~{dosimetry['inhaled_ug']} µg of fine particulates "
            f"(equivalent to {dosimetry['equivalent_clean_rest_hours']} hours of resting in clean air). "
            f"Switch to {top_indoor['name']} or postpone."
        )

    # Calculate clean window HES & Dose for direct comparison
    later_hes = calculate_hes(window_info["best_pm25_avg"], duration, activity_key)
    later_dosimetry = calculate_inhaled_dose_ug(window_info["best_pm25_avg"], duration, activity_key)

    return {
        "activity": activity_key,
        "activity_label": act_info["label"],
        "activity_icon": act_info["icon"],
        "region": region,
        "region_name": NEA_REGIONS[region]["name"],
        "pm25_1hr": current_pm25,
        "band": band,
        "status": status,
        "color": color,
        "action_headline": action,
        "guidance": guidance,
        "derived_hes": hes,
        "later_hes": later_hes,
        "duration_mins": duration,
        "sensitivity": sensitivity,
        "dosimetry": dosimetry,
        "later_dosimetry": later_dosimetry,
        "protective_guidance": protection,
        "regional_escape": regional_escape,
        "indoor_refuge": {
            "name": top_indoor["name"],
            "region_name": NEA_REGIONS[top_indoor["region"]]["name"],
            "effective_pm25": indoor_eff_pm25,
            "env_note": top_indoor["env_note"]
        },
        "clean_air_window": window_info,
        "forecast_12hr": forecast[:6],  # Next 6 hours preview
        "official_disclaimer": "Official NEA PM2.5 observations. Dosimetry & recommendations are non-medical respiratory ventilation estimates."
    }


def rank_clean_places(
    user_region: str,
    pm25_data: Dict[str, float],
    category: str = "all",
    duration_mins: int = 45
) -> List[Dict[str, Any]]:
    """
    Ranks outdoor parks and indoor air-filtered alternatives based on regional PM2.5
    AND real Haversine travel distance from the user's current region.
    """
    user_reg = user_region.lower() if user_region.lower() in NEA_REGIONS else "central"
    user_meta = NEA_REGIONS[user_reg]
    user_pm25 = float(pm25_data.get(user_reg, 50.0))

    ranked = []

    # 1. Include Indoor Filtered Venues when category == "indoor" or when category == "all" and air is elevated
    source_list = []
    if category == "indoor":
        source_list = [{**ind, "is_indoor": True} for ind in INDOOR_ALTERNATIVES]
    elif category == "all":
        source_list = [{**p, "is_indoor": False} for p in POPULAR_PLACES]
        if user_pm25 > 55.0:
            # Automatically surface top indoor refuges when outdoor air is elevated/high
            source_list.extend([{**ind, "is_indoor": True} for ind in INDOOR_ALTERNATIVES[:4]])
    else:
        source_list = [
            {**p, "is_indoor": False}
            for p in POPULAR_PLACES
            if p["category"] == category
        ]

    for place in source_list:
        p_reg = place["region"]
        outdoor_pm25 = float(pm25_data.get(p_reg, 50.0))
        is_indoor = place.get("is_indoor", False)

        # Effective PM2.5 inside filtered indoor venues vs open outdoor parks
        filtration = float(place.get("filtration_factor", 1.0)) if is_indoor else 1.0
        effective_pm25 = round(outdoor_pm25 * filtration, 1)

        band = get_pm25_band(effective_pm25)
        hes = calculate_hes(effective_pm25, duration_mins, "park")
        dose = calculate_inhaled_dose_ug(effective_pm25, duration_mins, "park")

        dist_km = round(haversine_km(user_meta["lat"], user_meta["lon"], place["lat"], place["lon"]), 1)
        diff = effective_pm25 - user_pm25

        if is_indoor:
            proximity = f"❄️ Filtered Indoor (~{int((1 - filtration) * 100)}% PM2.5 reduction) • {dist_km} km away"
        elif p_reg == user_reg:
            proximity = f"Local ({NEA_REGIONS[p_reg]['name']}) • ~{dist_km} km away"
        else:
            if abs(diff) < 1.0:
                diff_text = "same PM2.5"
            elif diff < 0:
                diff_text = f"{abs(diff):.0f} µg/m³ cleaner"
            else:
                diff_text = f"{diff:.0f} µg/m³ higher"
            proximity = f"{NEA_REGIONS[p_reg]['name']} Region ({diff_text}) • ~{dist_km} km"

        ranked.append({
            "id": place["id"],
            "name": place["name"],
            "region": p_reg,
            "region_name": NEA_REGIONS[p_reg]["name"],
            "category": place["category"],
            "is_indoor": is_indoor,
            "pm25_1hr": effective_pm25,
            "outdoor_regional_pm25": outdoor_pm25,
            "band": band,
            "hes_score": hes,
            "inhaled_ug": dose["inhaled_ug"],
            "distance_km": dist_km,
            "is_home_region": p_reg == user_reg,
            "proximity_note": proximity,
            "env_note": place.get("env_note", ""),
            "lat": place["lat"],
            "lon": place["lon"]
        })

    # Sort primarily by effective PM2.5 ascending, then by distance_km ascending
    ranked.sort(key=lambda x: (round(x["pm25_1hr"] / 5.0) * 5, x["distance_km"]))
    return ranked


def calculate_route_alternatives(
    origin: str,
    destination: str,
    origin_region: Optional[str] = None,
    dest_region: Optional[str] = None,
    pm25_data: Optional[Dict[str, float]] = None,
    weather: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Computes distance-accurate, shelter-aware journey options between any two Singapore locations.
    Automatically resolves locations from the 42-hub Singapore Gazetteer so travel times,
    distances, and outdoor minutes reflect real Singapore geography.
    """
    pm25_map = pm25_data or {"central": 60.0, "east": 60.0, "north": 50.0, "south": 55.0, "west": 60.0}

    orig_loc = resolve_sg_location(origin, origin_region or "east")
    dest_loc = resolve_sg_location(destination, dest_region or "central")

    # Respect explicit region override ONLY if location wasn't matched in the Gazetteer
    orig_reg = orig_loc["region"] if orig_loc.get("matched") else (origin_region or orig_loc["region"]).lower()
    dest_reg = dest_loc["region"] if dest_loc.get("matched") else (dest_region or dest_loc["region"]).lower()
    if orig_reg not in NEA_REGIONS:
        orig_reg = "east"
    if dest_reg not in NEA_REGIONS:
        dest_reg = "central"

    pm_orig = float(pm25_map.get(orig_reg, 65.0))
    pm_dest = float(pm25_map.get(dest_reg, 65.0))
    avg_pm = (pm_orig + pm_dest) / 2.0

    # Calculate real straight-line and transit corridor distance in km
    straight_km = haversine_km(orig_loc["lat"], orig_loc["lon"], dest_loc["lat"], dest_loc["lon"])
    if straight_km < 0.4 and orig_loc["name"].lower() != dest_loc["name"].lower():
        straight_km = 2.2  # Default neighborhood separation if both fell back to same region centroid
    corridor_km = round(max(0.8, straight_km * 1.28), 1)

    # Shelter coverage factor from origin & destination hubs (0.45 to 0.95)
    avg_shelter = (float(orig_loc.get("shelter_score", 0.75)) + float(dest_loc.get("shelter_score", 0.75))) / 2.0

    # --- MODE 1: MRT + Underground / Sheltered Walk2Ride Link ---
    # First/last mile access is ~10 mins total walk, reduced to 2-6 mins exposed outdoors based on hub shelter score
    mrt_in_cabin_min = max(6, round((corridor_km / 34.0) * 60) + 5)  # ~34 km/h average MRT speed + platform wait
    mrt_total_walk_min = 9
    mrt_outdoor_min = max(2, round(mrt_total_walk_min * (1.0 - avg_shelter * 0.72)))
    mrt_indoor_min = mrt_in_cabin_min + (mrt_total_walk_min - mrt_outdoor_min)
    mrt_total_min = mrt_outdoor_min + mrt_indoor_min

    # Effective exposure: outdoor walk at 100% ambient PM2.5 + filtered air-con cabin/mall at 28% ambient PM2.5
    mrt_equiv_outdoor_min = mrt_outdoor_min + (mrt_indoor_min * 0.22)
    mrt_hes = calculate_hes(avg_pm, mrt_equiv_outdoor_min, "commute")
    mrt_dose = calculate_inhaled_dose_ug(avg_pm, mrt_equiv_outdoor_min, "commute")

    # --- MODE 2: Public Bus (Roadside Stops & Transfers) ---
    bus_in_cabin_min = max(8, round((corridor_km / 19.5) * 60) + 4)  # ~19.5 km/h urban bus speed
    bus_outdoor_min = max(8, round(10 + (1.0 - avg_shelter) * 10))  # Walk to arterial road + open bus stop wait
    bus_total_min = bus_in_cabin_min + bus_outdoor_min
    bus_equiv_outdoor_min = bus_outdoor_min + (bus_in_cabin_min * 0.35)  # Bus doors open frequently at stops
    bus_hes = calculate_hes(avg_pm, bus_equiv_outdoor_min, "walk")
    bus_dose = calculate_inhaled_dose_ug(avg_pm, bus_equiv_outdoor_min, "walk")

    # --- MODE 3: Active Outdoor Mode (Direct Walk for <= 4.5 km, Outdoor Cycle / PCN for > 4.5 km) ---
    if corridor_km <= 4.5:
        active_mode_name = f"Direct Outdoor Walk ({corridor_km} km)"
        active_icon = "🚶"
        active_min = max(10, round((corridor_km / 4.8) * 60))
        active_act_key = "walk"
        active_transit_desc = "100% Outdoor Sidewalk & Traffic Crossings"
        active_steps = [
            f"Continuous {active_min} min ({corridor_km} km) outdoor walk from {orig_loc['name']} to {dest_loc['name']}",
            f"100% unfiltered ambient air exposure ({pm_orig:.0f}–{pm_dest:.0f} µg/m³) at 18 L/min walking ventilation"
        ]
    else:
        # For longer distances (e.g. Tampines to Marina Bay = 15.8 km), show realistic Park Connector Cycling AND full walk time note
        walk_full_min = round((corridor_km / 4.8) * 60)
        active_min = max(20, round((corridor_km / 17.5) * 60))
        active_mode_name = f"Outdoor Cycling / PCN ({corridor_km} km)"
        active_icon = "🚲"
        active_act_key = "cycle"
        active_transit_desc = f"100% Outdoor Park Connector / Road ({walk_full_min} min if walked)"
        active_steps = [
            f"{active_min} min outdoor ride across {corridor_km} km from {orig_loc['name']} to {dest_loc['name']} (walking would take ~{walk_full_min} min)",
            f"High cycling ventilation (36 L/min) in unfiltered outdoor air ({avg_pm:.0f} µg/m³)"
        ]

    active_hes = calculate_hes(avg_pm, active_min, active_act_key)
    active_dose = calculate_inhaled_dose_ug(avg_pm, active_min, active_act_key)

    dose_saved_pct = max(0, round(((active_dose["inhaled_ug"] - mrt_dose["inhaled_ug"]) / max(0.1, active_dose["inhaled_ug"])) * 100))

    routes = [
        {
            "id": "mrt_optimal",
            "name": f"MRT + {orig_loc.get('hub_type', 'Sheltered Link')}",
            "icon": "🚇",
            "recommended": True,
            "departure": "Leave now",
            "distance_km": corridor_km,
            "total_min": mrt_total_min,
            "outdoor_min": mrt_outdoor_min,
            "indoor_min": mrt_indoor_min,
            "transit_type": f"Air-conditioned MRT ({orig_loc.get('mrt', 'MRT')}) & Sheltered Linkways",
            "exposure_score": mrt_hes,
            "inhaled_ug": mrt_dose["inhaled_ug"],
            "dose_saved_pct": dose_saved_pct,
            "badge": f"🟢 BEST ({dose_saved_pct}% Less PM2.5 Inhaled)",
            "badge_color": "#10b981",
            "steps": [
                f"Access {orig_loc['name']} ({orig_loc.get('hub_type', 'Station')}) via sheltered link (~{max(1, mrt_outdoor_min // 2)} min exposed)",
                f"Air-conditioned MRT trunk ride ({mrt_in_cabin_min} min across {corridor_km} km; ~75% particulate filtration)",
                f"Arrive at {dest_loc['name']} ({dest_loc.get('hub_type', 'Hub')}) via underground/covered exit (~{mrt_outdoor_min - max(1, mrt_outdoor_min // 2)} min exposed)"
            ],
            "exposure_level": "LOW",
            "outdoor_pct": f"{round((mrt_outdoor_min / max(1, mrt_total_min)) * 100)}%"
        },
        {
            "id": "bus_transit",
            "name": f"Public Bus Corridor ({corridor_km} km)",
            "icon": "🚌",
            "recommended": False,
            "departure": "Leave now",
            "distance_km": corridor_km,
            "total_min": bus_total_min,
            "outdoor_min": bus_outdoor_min,
            "indoor_min": bus_in_cabin_min,
            "transit_type": "Bus ride + Roadside bus stop waiting",
            "exposure_score": bus_hes,
            "inhaled_ug": bus_dose["inhaled_ug"],
            " badge_raw": "MODERATE",
            "badge": "🟡 MODERATE EXPOSURE",
            "badge_color": "#f59e0b",
            "steps": [
                f"Walk outdoors to arterial bus stop in {orig_loc['name']} & wait at open-air roadside shelter (~{bus_outdoor_min} min total outdoor)",
                f"Bus journey ({bus_in_cabin_min} min across {corridor_km} km; frequent door openings along traffic corridor)",
                f"Alight near {dest_loc['name']} (~{bus_dose['inhaled_ug']} µg estimated PM2.5 inhaled)"
            ],
            "exposure_level": "MODERATE",
            "outdoor_pct": f"{round((bus_outdoor_min / max(1, bus_total_min)) * 100)}%"
        },
        {
            "id": "walk_direct",
            "name": active_mode_name,
            "icon": active_icon,
            "recommended": False,
            "departure": "Leave now",
            "distance_km": corridor_km,
            "total_min": active_min,
            "outdoor_min": active_min,
            "indoor_min": 0,
            "transit_type": active_transit_desc,
            "exposure_score": active_hes,
            "inhaled_ug": active_dose["inhaled_ug"],
            "badge": "🔴 HIGHEST EXPOSURE",
            "badge_color": "#ef4444",
            "steps": active_steps,
            "exposure_level": "HIGH",
            "outdoor_pct": "100%"
        }
    ]

    # Calculate timing alternative: Leave later during clean window
    now_hour = datetime.now(SGT).hour
    forecast = get_forecast_profile(avg_pm, now_hour, weather=weather)
    window = find_clean_air_window(forecast, activity_key="commute")

    future_hes = calculate_hes(window["best_pm25_avg"], mrt_equiv_outdoor_min, "commute")

    timing_recommendation = {
        "best_departure": window["best_window"].split(" – ")[0] if " – " in window["best_window"] else "Now",
        "clean_window": window["best_window"],
        "projected_pm25": window["best_pm25_avg"],
        "current_pm25": round(avg_pm, 1),
        "reduction_pct": window["reduction_pct"],
        "mrt_hes_now": routes[0]["exposure_score"],
        "mrt_hes_later": future_hes,
        "advice": window["recommendation"]
    }

    return {
        "origin": orig_loc["name"],
        "destination": dest_loc["name"],
        "origin_region": NEA_REGIONS[orig_reg]["name"],
        "dest_region": NEA_REGIONS[dest_reg]["name"],
        "origin_region_key": orig_reg,
        "dest_region_key": dest_reg,
        "origin_pm25": round(pm_orig, 1),
        "dest_pm25": round(pm_dest, 1),
        "origin_hub_type": orig_loc.get("hub_type", "MRT Station"),
        "dest_hub_type": dest_loc.get("hub_type", "MRT Station"),
        "distance_km": corridor_km,
        "avg_pm25": round(avg_pm, 1),
        "routes": routes,
        "timing_optimization": timing_recommendation
    }
