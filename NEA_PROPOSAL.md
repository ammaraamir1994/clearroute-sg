# ClearRoute SG (v2.0) — Executive Briefing for NEA

**Prepared for:** National Environment Agency (NEA) Singapore / Meteorological Service Singapore (MSS) / Open Government Products  
**Repository:** [https://github.com/ammaraamir1994/clearroute-sg](https://github.com/ammaraamir1994/clearroute-sg)  
**Subject:** ClearRoute SG — Actionable Personal Decision Layer Built on Official NEA Real-Time Feeds

---

## 1. The Problem: The "Observation-to-Decision" Gap

Singapore provides high-integrity environmental monitoring through myENV and data.gov.sg (1-hour $\text{PM}_{2.5}$, 24-hour PSI, rainfall, wind speed/direction, and air temperature). However, during elevated or transboundary haze episodes, citizens face a practical behavioral question that raw charts do not directly answer:

> *"I need to commute from Tampines to Marina Bay, or I want to take my kids outside / go for a 5 km run today. Should I go now, wait a few hours, take a different transit mode, or use an indoor venue?"*

**ClearRoute SG** is an open-source reference decision layer that translates official NEA real-time observations into **immediate location, route, and timing choices**.

---

## 2. Alignment with NEA Scientific & Public Communication Standards

1. **Honest Spatial Resolution (No False Hyperlocal Claims)**
   - Rather than fabricating street-level precision from 5 regional stations, ClearRoute SG strictly anchors ambient air quality to **NEA's 5 official monitoring sectors** (*Central, East, North, South, West*).
2. **Strict Separation of Official Data vs. Derived Models**
   - Official NEA 1-hr $\text{PM}_{2.5}$ bands (Band I Normal $\le 55$, Band II Elevated $56\text{–}150$, Band III High $151\text{–}250$, Band IV Very High $>250\ \mu\text{g/m}^3$) are preserved verbatim.
   - Derived metrics—such as estimated **Inhaled Particulate Dose ($\mu\text{g}$)** and **Haze Exposure Score ($\text{HES}$)**—are transparently labeled as **non-medical respiratory ventilation estimates**.
3. **Medically Sound Protective Guidance**
   - Explicitly warns users **never** to wear an N95 respirator during strenuous exercise (running/cycling), while advising appropriate N95 usage for prolonged low-exertion outdoor exposure in Elevated/High bands.

---

## 3. Core Technical Capabilities (v2.0)

### A. Activity-Specific Dosimetry ($\mu\text{g}$) & Sensitivity Profiles
- Models respiratory minute ventilation from resting/commuting ($14\text{ L/min}$) up to strenuous running ($52\text{ L/min}$):
  $$\text{Inhaled Dose ($\mu$g)} = \text{PM}_{2.5}\ (\mu\text{g/m}^3) \times \frac{\text{Ventilation (L/min)}}{1000} \times \text{Duration (min)}$$
- Includes customizable duration ($15\text{–}180\text{ min}$) and sensitivity profiles (*Standard Adult* vs. *Sensitive / Asthma / Elderly / Children*).

### B. 42-Hub Singapore Gazetteer & Sheltered Transit Routing
- Evaluates real corridor distances and **Walk2Ride / Underground Hub Shelter Scores** across 42 major Singapore MRT interchanges, town hubs, and business parks.
- Quantifies how switching from an open roadside bus/walk corridor to an **MRT + Underground Link** cuts inhaled particulate mass by **70–85%**.

### C. Heat-vs-Haze Aware "Clean Air Window"
- Ingests live NEA **Rainfall ($\text{mm}$)**, **Wind Speed/Direction**, and **Air Temperature ($^\circ\text{C}$)** alongside Singapore's diurnal boundary-layer dispersion curve.
- Incorporates an **Equatorial Heat-Stress Guardrail**: when morning air is already clean ($\le 35\ \mu\text{g/m}^3$), it prevents advising runners to delay workouts into $33^\circ\text{C}$ midday heat.

### D. Distance-Aware Cleanest Places & HEPA Indoor Refuges
- Ranks 16 outdoor parks by regional $\text{PM}_{2.5}$ and Haversine distance ($\text{km}$), while surfacing **8 HEPA / Air-Conditioned Indoor Active Refuges** (e.g., *Singapore Sports Hub, Our Tampines Hub, Gardens by the Bay Conservatories, Jewel Changi, CityLink Underground Loop*) when outdoor haze is elevated.

### E. Built-in Historical Haze Scenario Simulator
- Because most days in Singapore enjoy Band I (Normal) air quality, a header toggle allows NEA reviewers to test system behavior across:
  - 🟢 **Live NEA Real-Time API** (`data.gov.sg`)
  - 🟠 **Oct 2023 East-Central Sector Plume** (Regional gradient scenario)
  - 🟡 **Morning Inversion + Afternoon Rain Washout** (Timing optimization scenario)
  - 🔴 **Sept 2015 El Niño Transboundary Crisis** (Band III/IV severe haze scenario)

---

## 4. Potential Collaboration Pathways with NEA

1. **Public-Facing Decision Widget**: Integrating activity & commute exposure comparisons into myENV or public haze advisories.
2. **Micro-Sensor & MSS Forecast Coupling**: Plugging in NEA's high-density neighborhood PM2.5 sensors or MSS numerical dispersion forecasts as drop-in replacements for the regional baseline.
3. **Open-Source Civic Tech Reference**: Serving as a blueprint for how citizens can use `data.gov.sg` v2 real-time environmental APIs responsibly.
