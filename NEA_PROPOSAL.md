# ClearRoute SG — Presentation & Executive Summary for NEA

**Recipient:** National Environment Agency (NEA) / data.gov.sg Data Innovation Team  
**Subject:** ClearRoute SG — Decision-Layer MVP for Singapore Air Quality Data

---

## Executive Summary

Singapore provides high-integrity, real-time air quality data (1-hour PM2.5 and 24-hour PSI across 5 regional sectors) via data.gov.sg. However, during elevated haze episodes, ordinary citizens and commuters face a persistent decision gap:

> *"The PSI is 160, but I need to commute from Tampines to Marina Bay, or I want to exercise. When should I step outside, and how do I minimize my cumulative exposure?"*

**ClearRoute SG** demonstrates how official NEA observations can be translated into **actionable timing and location decisions** rather than just reporting raw indices.

---

## 1. Core Principles & Alignment with NEA Standards

1. **Honest Regional Resolution (No False Hyperlocal Claims)**:
   - ClearRoute strictly scopes its baseline measurements to the **5 official NEA monitoring regions** (Central, East, North, South, West) rather than extrapolating speculative street-level sensor numbers.
2. **Clear Separation of Official vs. Derived Logic**:
   - Official NEA bands and national advisories are preserved verbatim.
   - Derived metrics (such as the Haze Exposure Score $\text{HES}$) are explicitly labeled as **activity ventilation models**, not individual medical prescriptions.
3. **Behavioral Impact Over Raw Numbers**:
   - Compares physical transit modes (e.g. MRT with 4 min outdoor walk vs. 25 min roadside walk) to show how commuters can achieve immediate ~75% particulate inhalation reductions.

---

## 2. Technical Architecture

- **Backend**: Python 3.11+ / FastAPI
- **Data Ingestion**: Official data.gov.sg REST API endpoints (`/v1/environment/pm25` & `/v1/environment/psi`) with in-memory caching and persistent observation history.
- **Exposure Modeling**:
  $$\text{HES} = \frac{\text{PM2.5} \times \text{OutdoorMinutes} \times \text{VentilationMultiplier}}{100}$$
- **Timing Forecast (Clean Air Window)**: Diurnal particulate dispersion modeling identifying optimal low-exposure windows for daily planning.
- **Frontend**: Clean single-page application with responsive UI and Leaflet geospatial visualization.

---

## 3. Potential Collaboration Opportunities with NEA

1. **Hyperlocal Sensor Network Integration**: Ingestion of temporary or municipal micro-sensor testbeds as NEA expands neighborhood monitoring.
2. **Official Meteorological Coupling**: Integrating MSS (Meteorological Service Singapore) wind vector forecasts and precipitation radars into the route timing algorithm.
3. **Public Health Communications**: Offering ClearRoute as an open-source reference implementation for public-facing advisories during transboundary haze events.
