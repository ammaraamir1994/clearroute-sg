"""
Haze-Safe Singapore - Core Models, Gazetteer, Scenarios, and Dosimetry Constants
Defines regions, 40+ Singapore locations, indoor alternatives, activity ventilation rates,
historical haze scenarios, and exposure/dosimetry calculations.
"""
import math
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

# Singapore 5 NEA Regions coordinates (centroids)
NEA_REGIONS: Dict[str, Dict[str, Any]] = {
    "central": {
        "name": "Central",
        "lat": 1.3150,
        "lon": 103.8450,
        "description": "Marina Bay, CBD, Orchard, Bishan, Toa Payoh, Novena, Bugis"
    },
    "east": {
        "name": "East",
        "lat": 1.3450,
        "lon": 103.9400,
        "description": "Tampines, Bedok, Changi, Pasir Ris, Paya Lebar"
    },
    "north": {
        "name": "North",
        "lat": 1.4250,
        "lon": 103.8250,
        "description": "Woodlands, Yishun, Sembawang, Punggol, Sengkang"
    },
    "south": {
        "name": "South",
        "lat": 1.2750,
        "lon": 103.8150,
        "description": "HarbourFront, Sentosa, Queenstown, Tiong Bahru, One-North"
    },
    "west": {
        "name": "West",
        "lat": 1.3450,
        "lon": 103.7250,
        "description": "Jurong East, Clementi, Bukit Batok, Boon Lay, Tuas"
    }
}

# Comprehensive Singapore Gazetteer (42 Major MRT Hubs, Town Centres & Landmarks)
# shelter_score (0.0 to 1.0): fraction of first/last mile walk covered by underground links or Walk2Ride sheltered linkways
SG_GAZETTEER: List[Dict[str, Any]] = [
    # Central
    {"id": "marina_bay", "name": "Marina Bay", "region": "central", "lat": 1.2764, "lon": 103.8546, "mrt": "NSL/CCL/TEL", "shelter_score": 0.90, "hub_type": "Underground CBD Hub"},
    {"id": "raffles_place", "name": "Raffles Place", "region": "central", "lat": 1.2839, "lon": 103.8515, "mrt": "NSL/EWL", "shelter_score": 0.92, "hub_type": "Underground CBD Hub"},
    {"id": "orchard", "name": "Orchard", "region": "central", "lat": 1.3040, "lon": 103.8318, "mrt": "NSL/TEL", "shelter_score": 0.90, "hub_type": "Underground Mall Network"},
    {"id": "dhoby_ghaut", "name": "Dhoby Ghaut", "region": "central", "lat": 1.2993, "lon": 103.8458, "mrt": "NSL/NEL/CCL", "shelter_score": 0.88, "hub_type": "Underground Interchange"},
    {"id": "city_hall", "name": "City Hall", "region": "central", "lat": 1.2931, "lon": 103.8520, "mrt": "NSL/EWL", "shelter_score": 0.92, "hub_type": "CityLink Underground Network"},
    {"id": "bugis", "name": "Bugis", "region": "central", "lat": 1.3005, "lon": 103.8559, "mrt": "EWL/DTL", "shelter_score": 0.86, "hub_type": "Underground Integrated Hub"},
    {"id": "novena", "name": "Novena", "region": "central", "lat": 1.3204, "lon": 103.8438, "mrt": "NSL", "shelter_score": 0.85, "hub_type": "Underground Medical/Mall Hub"},
    {"id": "toa_payoh", "name": "Toa Payoh", "region": "central", "lat": 1.3326, "lon": 103.8475, "mrt": "NSL", "shelter_score": 0.82, "hub_type": "Integrated Town Hub"},
    {"id": "bishan", "name": "Bishan", "region": "central", "lat": 1.3513, "lon": 103.8491, "mrt": "NSL/CCL", "shelter_score": 0.78, "hub_type": "Town Interchange"},
    {"id": "ang_mo_kio", "name": "Ang Mo Kio", "region": "central", "lat": 1.3699, "lon": 103.8496, "mrt": "NSL", "shelter_score": 0.78, "hub_type": "Town Hub with Underpass"},
    {"id": "serangoon", "name": "Serangoon", "region": "central", "lat": 1.3497, "lon": 103.8737, "mrt": "NEL/CCL", "shelter_score": 0.85, "hub_type": "NEX Underground Integrated Hub"},
    {"id": "kallang", "name": "Kallang / Sports Hub", "region": "central", "lat": 1.3028, "lon": 103.8713, "mrt": "EWL/CCL", "shelter_score": 0.80, "hub_type": "Sheltered Stadium Concourse"},
    {"id": "botanic_gardens_mrt", "name": "Botanic Gardens", "region": "central", "lat": 1.3221, "lon": 103.8149, "mrt": "CCL/DTL", "shelter_score": 0.65, "hub_type": "Park Interchange"},

    # East
    {"id": "tampines", "name": "Tampines", "region": "east", "lat": 1.3533, "lon": 103.9452, "mrt": "EWL/DTL", "shelter_score": 0.82, "hub_type": "Regional Town Hub (3 Malls)"},
    {"id": "bedok", "name": "Bedok", "region": "east", "lat": 1.3240, "lon": 103.9302, "mrt": "EWL", "shelter_score": 0.80, "hub_type": "Integrated Mall/Bus Hub"},
    {"id": "paya_lebar", "name": "Paya Lebar", "region": "east", "lat": 1.3175, "lon": 103.8927, "mrt": "EWL/CCL", "shelter_score": 0.84, "hub_type": "PLQ Sheltered Commercial Hub"},
    {"id": "pasir_ris", "name": "Pasir Ris", "region": "east", "lat": 1.3731, "lon": 103.9493, "mrt": "EWL", "shelter_score": 0.75, "hub_type": "Town Centre Hub"},
    {"id": "changi_airport", "name": "Changi Airport / Jewel", "region": "east", "lat": 1.3573, "lon": 103.9888, "mrt": "EWL", "shelter_score": 0.95, "hub_type": "100% Indoor Climate-Controlled"},
    {"id": "changi_business_park", "name": "Expo / Changi Business Park", "region": "east", "lat": 1.3345, "lon": 103.9615, "mrt": "EWL/DTL", "shelter_score": 0.76, "hub_type": "Business Park Interchange"},
    {"id": "marine_parade", "name": "Marine Parade / Katong", "region": "east", "lat": 1.3026, "lon": 103.9072, "mrt": "TEL", "shelter_score": 0.82, "hub_type": "Underground TEL Station"},
    {"id": "east_coast", "name": "East Coast Park", "region": "east", "lat": 1.3010, "lon": 103.9122, "mrt": "TEL", "shelter_score": 0.45, "hub_type": "Coastal Park via Underpass"},

    # North & North-East
    {"id": "woodlands", "name": "Woodlands", "region": "north", "lat": 1.4369, "lon": 103.7865, "mrt": "NSL/TEL", "shelter_score": 0.84, "hub_type": "Regional Underground Interchange"},
    {"id": "yishun", "name": "Yishun", "region": "north", "lat": 1.4295, "lon": 103.8350, "mrt": "NSL", "shelter_score": 0.80, "hub_type": "Northpoint Integrated Hub"},
    {"id": "sembawang", "name": "Sembawang", "region": "north", "lat": 1.4491, "lon": 103.8201, "mrt": "NSL", "shelter_score": 0.72, "hub_type": "Sheltered Town Hub"},
    {"id": "punggol", "name": "Punggol", "region": "north", "lat": 1.4045, "lon": 103.9021, "mrt": "NEL/LRT", "shelter_score": 0.82, "hub_type": "Waterway Point Integrated Hub"},
    {"id": "sengkang", "name": "Sengkang", "region": "north", "lat": 1.3917, "lon": 103.8955, "mrt": "NEL/LRT", "shelter_score": 0.82, "hub_type": "Compass One Integrated Hub"},
    {"id": "hougang", "name": "Hougang", "region": "north", "lat": 1.3712, "lon": 103.8924, "mrt": "NEL", "shelter_score": 0.78, "hub_type": "Underground Town Station"},

    # South
    {"id": "harbourfront", "name": "HarbourFront / VivoCity", "region": "south", "lat": 1.2654, "lon": 103.8215, "mrt": "NEL/CCL", "shelter_score": 0.90, "hub_type": "Underground Megamall Hub"},
    {"id": "sentosa", "name": "Sentosa", "region": "south", "lat": 1.2540, "lon": 103.8238, "mrt": "Monorail", "shelter_score": 0.60, "hub_type": "Island Resort Transit"},
    {"id": "tiong_bahru", "name": "Tiong Bahru", "region": "south", "lat": 1.2861, "lon": 103.8270, "mrt": "EWL", "shelter_score": 0.80, "hub_type": "Underground Mall Station"},
    {"id": "queenstown", "name": "Queenstown", "region": "south", "lat": 1.2946, "lon": 103.8060, "mrt": "EWL", "shelter_score": 0.72, "hub_type": "Elevated Station with Linkways"},
    {"id": "one_north", "name": "one-north / Buona Vista", "region": "south", "lat": 1.3072, "lon": 103.7902, "mrt": "EWL/CCL", "shelter_score": 0.82, "hub_type": "Biopolis/Star Vista Hub"},
    {"id": "outtram_park", "name": "Outram Park / SGH", "region": "south", "lat": 1.2803, "lon": 103.8394, "mrt": "EWL/NEL/TEL", "shelter_score": 0.88, "hub_type": "3-Line Underground Interchange"},

    # West
    {"id": "jurong_east", "name": "Jurong East", "region": "west", "lat": 1.3331, "lon": 103.7422, "mrt": "NSL/EWL", "shelter_score": 0.88, "hub_type": "J-Walk Elevated Sheltered Network"},
    {"id": "clementi", "name": "Clementi", "region": "west", "lat": 1.3152, "lon": 103.7652, "mrt": "EWL", "shelter_score": 0.80, "hub_type": "Clementi Mall Integrated Hub"},
    {"id": "bukit_batok", "name": "Bukit Batok", "region": "west", "lat": 1.3490, "lon": 103.7496, "mrt": "NSL", "shelter_score": 0.74, "hub_type": "West Mall Town Hub"},
    {"id": "bukit_panjang", "name": "Bukit Panjang", "region": "west", "lat": 1.3790, "lon": 103.7615, "mrt": "DTL/LRT", "shelter_score": 0.82, "hub_type": "Hillion/BPP Integrated Hub"},
    {"id": "boon_lay", "name": "Boon Lay / Jurong Point", "region": "west", "lat": 1.3386, "lon": 103.7061, "mrt": "EWL", "shelter_score": 0.84, "hub_type": "Jurong Point Integrated Hub"},
    {"id": "nus_kent_ridge", "name": "Kent Ridge / NUS", "region": "west", "lat": 1.2935, "lon": 103.7845, "mrt": "CCL", "shelter_score": 0.85, "hub_type": "Underground NUH/NUS Station"},
    {"id": "tuas_link", "name": "Tuas", "region": "west", "lat": 1.3404, "lon": 103.6368, "mrt": "EWL", "shelter_score": 0.55, "hub_type": "Industrial West Terminus"}
]

# Singapore Popular Outdoor Places / Landmarks with micro-environment metadata
POPULAR_PLACES: List[Dict[str, Any]] = [
    {"id": "bishan_park", "name": "Bishan-Ang Mo Kio Park", "region": "central", "category": "park", "lat": 1.3626, "lon": 103.8471, "env_note": "Open riverine corridor; moderate tree canopy"},
    {"id": "marina_bay", "name": "Marina Bay Waterfront Promenade", "region": "central", "category": "outdoor", "lat": 1.2847, "lon": 103.8610, "env_note": "Bay breeze dispersion; immediate access to underground malls if haze spikes"},
    {"id": "botanic_gardens", "name": "Singapore Botanic Gardens", "region": "central", "category": "park", "lat": 1.3138, "lon": 103.8159, "env_note": "Dense heritage tree canopy; 2 MRT exits (CCL/DTL)"},
    {"id": "gardens_by_the_bay", "name": "Gardens by the Bay (Outdoor Gardens)", "region": "central", "category": "park", "lat": 1.2816, "lon": 103.8636, "env_note": "Waterfront ventilation; Cooled Conservatories on-site as indoor refuge"},
    {"id": "macritchie", "name": "MacRitchie Reservoir Boardwalk", "region": "central", "category": "nature", "lat": 1.3444, "lon": 103.8348, "env_note": "Dense secondary forest canopy; longer distance to indoor shelter"},
    {"id": "east_coast_park", "name": "East Coast Park", "region": "east", "category": "park", "lat": 1.3010, "lon": 103.9122, "env_note": "Strong coastal sea breeze; TEL MRT underpass access"},
    {"id": "bedok_reservoir", "name": "Bedok Reservoir Park", "region": "east", "category": "park", "lat": 1.3412, "lon": 103.9317, "env_note": "Open water body ventilation; 4.3 km loop next to DTL MRT"},
    {"id": "changi_beach", "name": "Changi Beach Park", "region": "east", "category": "outdoor", "lat": 1.3912, "lon": 103.9912, "env_note": "Johor Strait coastal breeze; low traffic emissions"},
    {"id": "jurong_lake", "name": "Jurong Lake Gardens", "region": "west", "category": "park", "lat": 1.3364, "lon": 103.7289, "env_note": "Open lakeside promenade; 5 min walk from Lakeside MRT"},
    {"id": "bukit_timah", "name": "Bukit Timah Nature Reserve", "region": "west", "category": "nature", "lat": 1.3547, "lon": 103.7764, "env_note": "Steep elevation (high exertion ventilation — avoid during elevated haze)"},
    {"id": "west_coast_park", "name": "West Coast Park", "region": "west", "category": "park", "lat": 1.2957, "lon": 103.7667, "env_note": "Southern coastal exposure; watch southwest wind plumes"},
    {"id": "woodlands_waterfront", "name": "Woodlands Waterfront Park", "region": "north", "category": "outdoor", "lat": 1.4532, "lon": 103.7847, "env_note": "Northernmost coastal promenade; often shielded from southern plumes"},
    {"id": "yishun_park", "name": "Yishun Park & Lower Seletar Reservoir", "region": "north", "category": "park", "lat": 1.4239, "lon": 103.8443, "env_note": "Shaded canopy and reservoir breeze in North sector"},
    {"id": "punggol_waterway", "name": "Punggol Waterway Park", "region": "north", "category": "park", "lat": 1.4085, "lon": 103.9050, "env_note": "Sheltered waterway corridor with LRT/Waterway Point access"},
    {"id": "southern_ridges", "name": "Southern Ridges / Mount Faber", "region": "south", "category": "nature", "lat": 1.2770, "lon": 103.8164, "env_note": "Elevated ridge walk; exposed to strait winds"},
    {"id": "sentosa_beach", "name": "Sentosa Siloso & Palawan Beach", "region": "south", "category": "outdoor", "lat": 1.2530, "lon": 103.8120, "env_note": "Open southern seafront"}
]

# Filtered / Climate-Controlled Indoor Alternatives when Haze is Elevated/High across Singapore
INDOOR_ALTERNATIVES: List[Dict[str, Any]] = [
    {
        "id": "gardens_domes",
        "name": "Flower Dome & Cloud Forest (Gardens by the Bay)",
        "region": "central",
        "category": "indoor",
        "lat": 1.2846,
        "lon": 103.8647,
        "filtration_factor": 0.18,
        "suitable_for": ["walk", "park", "kids"],
        "env_note": "Chilled, HEPA-grade air handling (~80% lower indoor PM2.5 than outdoors)"
    },
    {
        "id": "jewel_changi",
        "name": "Jewel Changi Shiseido Forest Valley & Canopy Park",
        "region": "east",
        "category": "indoor",
        "lat": 1.3602,
        "lon": 103.9898,
        "filtration_factor": 0.15,
        "suitable_for": ["walk", "run", "park", "kids"],
        "env_note": "Massive indoor terraced forest trails with airport-grade MERV-14 air filtration"
    },
    {
        "id": "sports_hub_indoor",
        "name": "Singapore Sports Hub (100PLUS Promenade & ActiveSG Gym)",
        "region": "central",
        "category": "indoor",
        "lat": 1.3040,
        "lon": 103.8742,
        "filtration_factor": 0.30,
        "suitable_for": ["run", "sports", "walk"],
        "env_note": "888m sheltered all-weather running track + indoor air-conditioned sports halls"
    },
    {
        "id": "tampines_hub",
        "name": "Our Tampines Hub (Indoor Sky Terrace & Sports Halls)",
        "region": "east",
        "category": "indoor",
        "lat": 1.3529,
        "lon": 103.9404,
        "filtration_factor": 0.25,
        "suitable_for": ["run", "sports", "kids", "walk"],
        "env_note": "Integrated community hub with air-conditioned courts, gym, and sheltered jogging loop"
    },
    {
        "id": "citylink_marina_loop",
        "name": "City Hall – Marina Square – Suntec – Millenia Underground Loop",
        "region": "central",
        "category": "indoor",
        "lat": 1.2925,
        "lon": 103.8555,
        "filtration_factor": 0.20,
        "suitable_for": ["walk", "commute", "kids"],
        "env_note": "Over 3.5 km of continuous underground air-conditioned pedestrian walkways"
    },
    {
        "id": "jurong_jwalk",
        "name": "Jurong East J-Walk Indoor Mall Network (JEM / Westgate / IMM)",
        "region": "west",
        "category": "indoor",
        "lat": 1.3334,
        "lon": 103.7431,
        "filtration_factor": 0.22,
        "suitable_for": ["walk", "kids", "commute"],
        "env_note": "Continuous elevated & indoor air-conditioned linkways across 3 major malls + Ng Teng Fong Hospital"
    },
    {
        "id": "canberra_bukit_indoor",
        "name": "Bukit Canberra Indoor ActiveSG Sport Hall",
        "region": "north",
        "category": "indoor",
        "lat": 1.4480,
        "lon": 103.8285,
        "filtration_factor": 0.22,
        "suitable_for": ["sports", "run", "kids"],
        "env_note": "Modern indoor sports arena and fitness gym serving North region residents"
    },
    {
        "id": "vivocity_harbourfront",
        "name": "VivoCity & HarbourFront Indoor Concourse",
        "region": "south",
        "category": "indoor",
        "lat": 1.2644,
        "lon": 103.8222,
        "filtration_factor": 0.20,
        "suitable_for": ["walk", "kids", "commute"],
        "env_note": "Direct NEL/CCL underground entry with wide indoor walking promenades"
    }
]

# Historical & Demo Haze Scenarios for Testing & NEA Review on Clear Days
HAZE_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "live": {
        "id": "live",
        "name": "🟢 Live NEA Real-Time API",
        "badge": "Live Feed",
        "description": "Real-time observations streamed directly from data.gov.sg (PM2.5, PSI, Rainfall, Wind, Temp)."
    },
    "severe_2015": {
        "id": "severe_2015",
        "name": "🔴 Sept 2015 El Niño Transboundary Crisis",
        "badge": "Historical Crisis Simulation",
        "description": "Simulates the September 2015 severe Southwest monsoon haze plume where 1-hr PM2.5 crossed Band III/IV across Southern & Western Singapore.",
        "pm25": {"central": 195.0, "east": 142.0, "north": 118.0, "south": 245.0, "west": 268.0},
        "psi": {"central": 248.0, "east": 198.0, "north": 176.0, "south": 292.0, "west": 315.0},
        "weather": {
            "temp_c": 31.8,
            "humidity_pct": 62.0,
            "wind_speed_kmh": 14.5,
            "wind_direction": "SW",
            "rainfall_mm": 0.0,
            "condition": "Dry Southwest Monsoon Plume (No rain washout)"
        }
    },
    "east_plume_2023": {
        "id": "east_plume_2023",
        "name": "🟠 Oct 2023 East-Central Sector Plume",
        "badge": "Regional Gradient Simulation",
        "description": "Simulates the October 2023 episode where East & Central Singapore experienced Elevated Band II PM2.5 while North & West remained in Normal Band I.",
        "pm25": {"central": 94.0, "east": 128.0, "north": 38.0, "south": 78.0, "west": 42.0},
        "psi": {"central": 112.0, "east": 138.0, "north": 64.0, "south": 96.0, "west": 68.0},
        "weather": {
            "temp_c": 30.5,
            "humidity_pct": 74.0,
            "wind_speed_kmh": 11.0,
            "wind_direction": "SE",
            "rainfall_mm": 0.2,
            "condition": "Southeasterly Breeze — Strong Regional Gradient (North/West clean)"
        }
    },
    "morning_inversion": {
        "id": "morning_inversion",
        "name": "🟡 Elevated Morning Inversion + Afternoon Rain Clearing",
        "badge": "Timing Optimization Demo",
        "description": "Stagnant morning boundary layer traps particulates (~78 µg/m³), followed by forecasted afternoon sea-breeze and convective shower washout.",
        "pm25": {"central": 82.0, "east": 74.0, "north": 68.0, "south": 79.0, "west": 86.0},
        "psi": {"central": 95.0, "east": 88.0, "north": 82.0, "south": 92.0, "west": 98.0},
        "weather": {
            "temp_c": 28.4,
            "humidity_pct": 84.0,
            "wind_speed_kmh": 6.5,
            "wind_direction": "VAR",
            "rainfall_mm": 4.5,
            "condition": "Passing Convective Showers — Active Wet Deposition Clearing Air"
        }
    }
}

# Activity Inhalation / Exposure multipliers & Minute Ventilation rates (L/min)
# Standard resting adult breathes ~7-8 L/min.
# Strenuous running increases minute ventilation to ~50-60 L/min AND shifts from nasal to oral breathing (bypassing nasal filtration).
ACTIVITY_FACTORS: Dict[str, Dict[str, Any]] = {
    "run": {
        "label": "Running",
        "factor": 3.0,
        "ventilation_lpm": 52.0,
        "default_mins": 35,
        "icon": "🏃",
        "heat_sensitive": True
    },
    "walk": {
        "label": "Walking",
        "factor": 1.5,
        "ventilation_lpm": 18.0,
        "default_mins": 25,
        "icon": "🚶",
        "heat_sensitive": False
    },
    "cycle": {
        "label": "Cycling",
        "factor": 2.2,
        "ventilation_lpm": 36.0,
        "default_mins": 45,
        "icon": "🚲",
        "heat_sensitive": True
    },
    "commute": {
        "label": "Commuting",
        "factor": 1.2,
        "ventilation_lpm": 14.0,
        "default_mins": 30,
        "icon": "🚇",
        "heat_sensitive": False
    },
    "sports": {
        "label": "Outdoor Sports",
        "factor": 2.8,
        "ventilation_lpm": 48.0,
        "default_mins": 60,
        "icon": "⚽",
        "heat_sensitive": True
    },
    "kids": {
        "label": "Taking Children Outside",
        "factor": 2.0,
        "ventilation_lpm": 22.0,
        "default_mins": 40,
        "icon": "👶",
        "heat_sensitive": True
    },
    "park": {
        "label": "Visiting Park / Relaxing",
        "factor": 1.2,
        "ventilation_lpm": 14.0,
        "default_mins": 45,
        "icon": "🌳",
        "heat_sensitive": False
    }
}


def get_pm25_band(pm25: float) -> Dict[str, str]:
    """
    Official Singapore NEA 1-hr PM2.5 bands (with sub-tier for moderate awareness):
    0 - 55: Band I (Normal) -> 🟢 Lower exposure
    56 - 150: Band II (Elevated) -> 🟡 Moderate (56-100) / 🟠 Elevated (101-150)
    151 - 250: Band III (High) -> 🔴 High exposure
    > 250: Band IV (Very High) -> 🟣 Very High exposure
    """
    if pm25 <= 55:
        return {
            "level": "LOWER",
            "nea_band": "Band I (Normal)",
            "badge": "🟢 Normal / Lower",
            "color": "#10b981",
            "desc": "Normal air quality (0–55 µg/m³)"
        }
    elif pm25 <= 100:
        return {
            "level": "MODERATE",
            "nea_band": "Band II (Elevated - Lower Tier)",
            "badge": "🟡 Moderate / Elevated",
            "color": "#f59e0b",
            "desc": "Elevated Band II (56–150 µg/m³) — Reduce prolonged exertion if sensitive"
        }
    elif pm25 <= 150:
        return {
            "level": "ELEVATED",
            "nea_band": "Band II (Elevated)",
            "badge": "🟠 Elevated",
            "color": "#f97316",
            "desc": "Elevated Band II (56–150 µg/m³) — Reduce strenuous outdoor activity"
        }
    elif pm25 <= 250:
        return {
            "level": "HIGH",
            "nea_band": "Band III (High)",
            "badge": "🔴 High",
            "color": "#ef4444",
            "desc": "High Band III (151–250 µg/m³) — Minimize prolonged outdoor exertion"
        }
    else:
        return {
            "level": "VERY_HIGH",
            "nea_band": "Band IV (Very High)",
            "badge": "🟣 Very High",
            "color": "#8b5cf6",
            "desc": "Very High Band IV (>250 µg/m³) — Avoid outdoor physical activities"
        }


def calculate_hes(pm25: float, outdoor_minutes: float, activity_type: str = "walk") -> float:
    """
    Calculate Haze Exposure Score (HES)
    HES = (PM2.5 * outdoor_minutes * activity_factor) / 100
    Normalized to an intuitive scale (0 - 100+).
    """
    factor = ACTIVITY_FACTORS.get(activity_type, {}).get("factor", 1.5)
    hes = (pm25 * outdoor_minutes * factor) / 100.0
    return round(hes, 1)


def calculate_inhaled_dose_ug(pm25: float, outdoor_minutes: float, activity_type: str = "walk") -> Dict[str, Any]:
    """
    Calculates tangible estimated PM2.5 mass inhaled in micrograms (µg)
    based on activity respiratory minute ventilation (L/min).
    1 m³ = 1,000 Liters.
    Dose (µg) = PM2.5 (µg/m³) * (Ventilation_L_per_min / 1000) * outdoor_minutes
    """
    act = ACTIVITY_FACTORS.get(activity_type, ACTIVITY_FACTORS["walk"])
    lpm = float(act.get("ventilation_lpm", 18.0))
    total_air_liters = lpm * outdoor_minutes
    total_air_m3 = total_air_liters / 1000.0
    inhaled_ug = pm25 * total_air_m3

    # Reference baseline: What a person at rest (8 L/min) inhales over 1 hour in clean WHO guideline air (15 µg/m³)
    # 15 * 0.008 * 60 = 7.2 µg/hr
    resting_clean_hr_ug = 7.2
    equivalent_clean_hours = round(inhaled_ug / resting_clean_hr_ug, 1)

    return {
        "inhaled_ug": round(inhaled_ug, 1),
        "ventilation_lpm": round(lpm, 0),
        "total_air_liters": round(total_air_liters, 0),
        "equivalent_clean_rest_hours": equivalent_clean_hours
    }


def get_protective_guidance(
    pm25: float,
    activity_type: str,
    sensitivity: str = "standard",
    inhaled_ug: float = 0.0
) -> Dict[str, str]:
    """
    Provides practical, real-world protective steps (N95 mask policy, indoor air purifier,
    and WHO/NEA threshold context) tailored to whether the user is doing strenuous exercise or commuting.
    """
    act = ACTIVITY_FACTORS.get(activity_type, ACTIVITY_FACTORS["walk"])
    is_strenuous = act["factor"] >= 2.0
    is_sensitive = sensitivity == "sensitive" or activity_type == "kids"

    # Mask guidance (crucial medical reality: NEVER wear an N95 mask while running/strenuous exercise!)
    if pm25 <= 55:
        if is_sensitive and pm25 > 35:
            mask_advice = "No mask needed for short trips; sensitive individuals may prefer air-conditioned transit."
        else:
            mask_advice = "No mask required. Air quality is within NEA Band I (Normal)."
    elif pm25 <= 100:
        if is_strenuous:
            mask_advice = "Do NOT wear an N95 mask during strenuous running/cycling (restricts breathing). Pace effort or move to an indoor gym."
        elif is_sensitive:
            mask_advice = "Sensitive groups (asthma/elderly/pregnant) should consider an EN149 FFP2 / NIOSH N95 mask if outdoors > 30 mins."
        else:
            mask_advice = "Mask not required for short walks; minimize lingering near busy traffic junctions."
    elif pm25 <= 150:
        if is_strenuous:
            mask_advice = "Switch to an indoor filtered gym. Do NOT run with an N95 mask as it increases cardiac & breathing strain."
        else:
            mask_advice = "Wear a well-fitted N95 / KN95 mask if you must stay outdoors for prolonged periods (>30 mins). Surgical masks do not filter PM2.5."
    else:
        if is_strenuous:
            mask_advice = "Cancel outdoor exercise immediately. Do not attempt strenuous workouts in an N95 mask."
        else:
            mask_advice = "N95 respirator strongly recommended for any unavoidable outdoor errands. Vulnerable individuals should remain indoors."

    # Indoor / Home environment tip
    if pm25 <= 55:
        indoor_advice = "Natural ventilation: Safe to open windows and air out living spaces."
    elif pm25 <= 100:
        indoor_advice = "Keep windows partially closed facing windward directions; run HEPA air purifiers on Auto/Medium in bedrooms."
    else:
        indoor_advice = "Close all windows/doors, switch AC to recirculation mode, and run HEPA air purifiers (CADR matched to room size) on High."

    return {
        "mask_guidance": mask_advice,
        "indoor_guidance": indoor_advice,
        "who_context": (
            f"Within WHO 24-hr guideline (15 µg/m³)"
            if pm25 <= 15
            else f"{round(pm25 / 15.0, 1)}x the WHO 24-hr reference (15 µg/m³); {get_pm25_band(pm25)['nea_band']}"
        )
    }


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in kilometers between two coordinates in Singapore."""
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def resolve_sg_location(query: str, fallback_region: str = "central") -> Dict[str, Any]:
    """
    Matches a user location string (e.g., 'Tampines', 'Marina Bay', 'Jurong East', 'NUS')
    against SG_GAZETTEER and POPULAR_PLACES. Automatically resolves coordinates, NEA region,
    MRT connectivity, and sheltered linkway score.
    """
    q = (query or "").strip().lower()
    if not q:
        reg = fallback_region.lower() if fallback_region.lower() in NEA_REGIONS else "central"
        meta = NEA_REGIONS[reg]
        return {
            "name": meta["name"],
            "region": reg,
            "lat": meta["lat"],
            "lon": meta["lon"],
            "mrt": "MRT Network",
            "shelter_score": 0.75,
            "hub_type": "Regional Sector",
            "matched": False
        }

    # 1. Exact ID or name match in Gazetteer
    for loc in SG_GAZETTEER:
        if q == loc["id"] or q == loc["name"].lower():
            return {**loc, "matched": True}

    # 2. Substring match in Gazetteer
    for loc in SG_GAZETTEER:
        if q in loc["name"].lower() or loc["name"].lower() in q or q.replace(" ", "_") == loc["id"]:
            return {**loc, "matched": True}

    # 3. Check Popular Places
    for place in POPULAR_PLACES:
        if q in place["name"].lower() or place["name"].lower() in q:
            return {
                "id": place["id"],
                "name": place["name"],
                "region": place["region"],
                "lat": place["lat"],
                "lon": place["lon"],
                "mrt": "Nearby Bus/MRT",
                "shelter_score": 0.55,
                "hub_type": "Outdoor Park / Landmark",
                "matched": True
            }

    # 4. Fallback to specified region centroid
    reg = fallback_region.lower() if fallback_region.lower() in NEA_REGIONS else "central"
    # Also check if query mentions one of the region names or descriptions
    for reg_key, reg_meta in NEA_REGIONS.items():
        if reg_key in q or q in reg_meta["description"].lower():
            reg = reg_key
            break

    meta = NEA_REGIONS[reg]
    return {
        "id": q.replace(" ", "_"),
        "name": query.strip().title(),
        "region": reg,
        "lat": meta["lat"],
        "lon": meta["lon"],
        "mrt": "MRT / Bus",
        "shelter_score": 0.72,
        "hub_type": f"{meta['name']} Neighborhood",
        "matched": False
    }


class AirQualityObservation(BaseModel):
    region: str
    pm25_1hr: float
    psi_24hr: Optional[float] = None
    band: Dict[str, str]
    timestamp: str


class DecisionCard(BaseModel):
    activity: str
    status: str
    color: str
    headline: str
    recommendation: str
    official_context: str
    derived_hes: float
    best_time_window: Optional[str] = None


class RouteOption(BaseModel):
    mode: str
    mode_name: str
    total_duration_min: int
    outdoor_duration_min: int
    indoor_duration_min: int
    hes_score: float
    badge: str
    color: str
    route_summary: str
    steps: List[str]


class CleanPlaceOption(BaseModel):
    name: str
    region: str
    category: str
    pm25_1hr: float
    band: Dict[str, str]
    hes_sample: float
    distance_note: Optional[str] = None
