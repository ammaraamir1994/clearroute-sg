# 🌿 ClearRoute SG (Haze-Safe Singapore) — Decision Layer v2.0

> **"I need to go from A to B, or I want to exercise today. When should I go, and which route or venue minimizes my inhaled PM2.5 dose?"**

ClearRoute SG transforms official Singapore **National Environment Agency (NEA)** air-quality and meteorological observations into **actionable personal timing, route, and location decisions**. Rather than just displaying raw PSI/PM2.5 numbers, it computes respiratory inhaled dose ($\mu\text{g}$), evaluates Singapore's sheltered underground transit corridors, balances equatorial heat stress against haze dispersion, and surfaces HEPA/AC indoor refuges.

---

## 1. Key Capabilities (v2.0)

### A. Personalized "Should I Go Outside Now?" + Respiratory Dosimetry ($\mu\text{g}$)
- Evaluates 7 core activities with realistic physiological minute ventilation ($\text{L/min}$):
  - 🏃 **Running** ($52\text{ L/min}$, $3.0\times$ factor)
  - ⚽ **Outdoor Sports** ($48\text{ L/min}$, $2.8\times$ factor)
  - 🚲 **Cycling** ($36\text{ L/min}$, $2.2\times$ factor)
  - 👶 **Kids Outdoors** ($22\text{ L/min}$, $2.0\times$ factor)
  - 🚶 **Walking** ($18\text{ L/min}$, $1.5\times$ factor)
  - 🚇 **Commuting** / 🌳 **Visiting Park** ($14\text{ L/min}$, $1.2\times$ factor)
- **Interactive Duration Slider ($15\text{–}180\text{ min}$) & Sensitivity Profile** (*Standard Adult* vs. *Sensitive / Asthma / Elderly*).
- **Tangible Dosimetry**: Calculates actual estimated **Inhaled PM2.5 Mass ($\mu\text{g}$)**:
  $$\text{Inhaled Dose ($\mu$g)} = \text{PM2.5 ($\mu$g/m$^3$)} \times \frac{\text{MinuteVentilation (L/min)}}{1000} \times \text{Duration (min)}$$
- **Practical Protective Guidance**: Actionable N95 respirator guidance (including why N95 masks should *not* be worn during strenuous running/cycling), home HEPA purifier advice, and WHO 24-hr ($15\ \mu\text{g/m}^3$) vs. NEA 1-hr Band context.

### B. Gazetteer-Backed Singapore Low-Exposure Journey Planner (40+ Hubs)
- Built-in gazetteer of **42 major Singapore MRT interchanges, town hubs, business parks, and landmarks** with real geodesic coordinates, automatic NEA region assignment, and **Walk2Ride / Underground Hub Shelter Scores**.
- Calculates **distance-accurate travel times and exposed outdoor minutes** (e.g., distinguishing a $1.1\text{ km}$ Bugis $\rightarrow$ City Hall underground walk from a $16\text{ km}$ Tampines $\rightarrow$ Marina Bay MRT commute).
- Compares **MRT + Underground Link** vs. **Public Bus** vs. **100% Outdoor Walk / Park Connector Cycle** by total **Inhaled Dose ($\mu\text{g}$)** and **% Particulate Reduction**.

### C. Multi-Factor "Clean Air Window" (Live Weather + Heat-vs-Haze Trade-off)
- Streams live NEA meteorological feeds from `data.gov.sg`: **Rainfall ($\text{mm}$)**, **Wind Speed ($\text{km/h}$)**, **Wind Direction**, and **Air Temperature ($^\circ\text{C}$)**.
- Models wet deposition (rain washout) and wind dispersion alongside Singapore's diurnal boundary layer curve.
- **Equatorial Heat-Stress Awareness**: Prevents counterproductive advice—when morning air is already clean ($\le 35\ \mu\text{g/m}^3$), it will *not* tell runners to wait until 2:00 PM ($33^\circ\text{C}$ peak UV/heat stress) to save $3\ \mu\text{g/m}^3$.

### D. Distance-Aware Cleanest Places & HEPA Indoor Refuges
- Ranks 16 popular Singapore outdoor parks and waterfronts by regional PM2.5 **and Haversine distance ($\text{km}$)** from the user's sector.
- Automatically surfaces **8 Climate-Controlled / HEPA Indoor Active Refuges** (e.g., *Gardens by the Bay Cooled Conservatories, Jewel Changi Forest Valley, Singapore Sports Hub 100PLUS Promenade, Our Tampines Hub, CityLink Underground Loop, Jurong J-Walk*) with effective indoor filtered PM2.5 when outdoor haze is elevated.

### E. Live NEA Feed + Historical Haze Crisis Simulator
- Header switcher lets users and NEA reviewers toggle between:
  - 🟢 **Live NEA Real-Time API** (`data.gov.sg`)
  - 🔴 **Sept 2015 El Niño Transboundary Crisis** (Band III/IV severe Southwest plume)
  - 🟠 **Oct 2023 East-Central Sector Plume** (Strong regional gradient where North/West remain clean)
  - 🟡 **Elevated Morning Inversion + Afternoon Rain Washout**

---

## 2. Architecture & File Structure

```
Haze-Safe SG/
├── backend/
│   ├── models.py            # 42-hub SG Gazetteer, indoor refuges, scenarios, dosimetry (µg) & HES
│   ├── nea_service.py       # Live data.gov.sg PM2.5, PSI & Weather client + Heat-vs-Haze forecast
│   ├── decision_engine.py   # Decision card generator, distance-based route optimizer & place ranker
│   ├── storage.py           # SQLite persistence for historical NEA observation auditing
│   └── main.py              # FastAPI application & REST endpoints
├── static/
│   └── index.html           # Responsive SPA with Leaflet dark map, scenario switcher & controls
├── tests/
│   └── test_engine.py       # Unit & async test suite covering all decision, route & weather models
├── Dockerfile               # Production container config with healthcheck
├── NEA_PROPOSAL.md          # Executive briefing for NEA / GovTech reviewers
└── requirements.txt         # Project dependencies
```

---

## 3. Quickstart & Running the App

### Run the Server Locally
```bash
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

Open your browser to:
- **Web App**: [http://localhost:8000](http://localhost:8000)
- **Interactive API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Run Unit Tests
```bash
PYTHONPATH=. venv/bin/pytest tests/ -v
```
