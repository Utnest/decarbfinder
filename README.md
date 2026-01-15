# decarbfinder
# AI‑Assisted Energy Transition Simulator

## 1. Project Overview

### What is this project?

This project is an **AI‑assisted, visual decision‑support system** designed to help municipalities or local governments explore the transition from carbon‑based energy sources to clean energy.

Rather than attempting to *predict the future*, the system allows users to **experiment with scenarios**, understand **trade‑offs**, and identify **failure modes** when transitioning an energy grid.

The tool answers questions such as:

* What happens to grid reliability if we phase out natural gas?
* How much storage is required to support high solar penetration?
* What is the cost vs emissions trade‑off?
* Which transition plans are *viable* and which ones fail?

This is **not** a real‑time grid controller or a national‑scale simulator. It is a **credible, scoped digital twin** suitable for academic, educational, and early policy‑planning use.

---

## 2. Why This Project Exists

Most energy‑related student projects focus on:

* Single predictions (e.g., demand forecasting)
* Emissions reduction only
* Overly simplified assumptions

Real decision‑makers care about:

* Reliability
* Cost
* Risk
* Trade‑offs

This project exists to bridge that gap by combining:

* Energy system simulation
* Optimization‑based AI
* Clear visual explanations

---

## 3. What Makes This an “AI” System

This project **intentionally avoids fake or buzzword AI**.

AI is used where it adds *real value*:

### AI Components

1. **Demand Forecasting (Optional ML)**

   * Learns demand trends from historical data
   * Produces forecasts with uncertainty

2. **Multi‑Objective Optimization (Core AI)**

   * Generates multiple energy transition scenarios
   * Optimizes across competing objectives:

     * Cost
     * Emissions
     * Reliability

3. **Scenario Exploration & Explanation**

   * The system explains *why* a scenario succeeds or fails

No deep reinforcement learning or large neural networks are required.

---

## 4. Project Scope (Very Important)

### Geographic Scope

* **Single region only** (city, province, or ISO)
* Examples:

  * Ontario
  * California (CAISO)
  * Texas (ERCOT)

### Time Horizon

* 2025 → 2050
* Annual resolution for long‑term planning
* Hourly simulation used only for stress testing

### Energy Sources Included

* Natural Gas (baseline / transitional)
* Solar
* Wind
* Battery Storage

This is sufficient to capture real‑world complexity without overengineering.

---

## 5. System Architecture

```
User Interface (Dashboard)
        ↓
AI Scenario Generator (Optimization)
        ↓
Energy System Simulation Core
        ↓
Reliability & Stress Testing
        ↓
Visual Results + Explanations
```

Each layer is modular and can be developed independently.

---

## 6. Core Modules Explained

### Module 1: Demand Modeling

**Purpose:** Estimate future electricity demand.

**Inputs:**

* Historical load data
* Population growth assumptions
* Electrification factors (EVs, heating)

**Methods:**

* Simple regression or gradient boosting
* Scenario‑based growth multipliers

**Outputs:**

* Annual demand projections
* Optional hourly demand profiles for stress testing

**Why this matters:** Understanding demand is foundational. Overestimating or underestimating demand breaks all downstream results.

---

### Module 2: Supply & Generation Modeling

**Purpose:** Represent how electricity is produced.

Each energy source is modeled using:

* Installed capacity (MW)
* Capacity factor
* Cost (CAPEX + OPEX)
* Emissions intensity
* Lifetime

The model simulates annual energy production and available capacity.

**Why this matters:** This module reveals:

* Baseload vs intermittent generation
* Why renewables alone are insufficient without storage
* Cost scaling effects

---

### Module 3: Storage Modeling

**Purpose:** Capture the role of batteries in balancing the grid.

**Key elements:**

* Energy capacity (MWh)
* Power capacity (MW)
* Charge/discharge efficiency
* Cost

Storage is dispatched to reduce unmet demand and smooth renewable output.

**Why this matters:** Storage is often underestimated in policy discussions. This module shows its true impact and cost.

---

### Module 4: Grid Reliability & Stress Testing

**Purpose:** Measure whether the grid actually works.

**Metrics:**

* Unmet demand (MWh)
* Reserve margin
* Loss of load probability

**Stress tests:**

* Peak winter demand
* Summer heatwaves
* Low renewable output scenarios

**Why this matters:** This module differentiates this project from typical student work. It exposes *failure modes*, not just success stories.

---

### Module 5: AI Scenario Generator (Core AI)

**Purpose:** Generate viable energy transition pathways.

**Method:** Multi‑objective optimization

**Objectives:**

* Minimize total cost
* Minimize emissions
* Maintain reliability constraints

**Outputs:**

* Low‑cost scenario
* Low‑emissions scenario
* High‑reliability scenario

**Why this matters:** This is where AI adds decision‑making value rather than prediction hype.

---

### Module 6: Visualization & User Interface

**Purpose:** Make results understandable to non‑technical users.

**Key visuals:**

* Energy mix over time (stacked area chart)
* Cost vs emissions trade‑off plot
* Grid stress heatmap
* Scenario comparison tables

**Interface:**

* Sliders for policy targets
* Scenario selection buttons
* Auto‑generated explanations

---

## 7. Technology Stack (All Free)

### Programming

* Python 3

### Modeling & AI

* pandas, numpy
* scikit‑learn
* CVXPY or Pyomo
* PyPSA (optional)

### Visualization

* Streamlit
* Plotly

### Data Sources

* Government energy agencies (free)
* Open Power System Data
* NREL renewable profiles

No paid APIs or cloud infrastructure required.

---

## 8. What This Project Does NOT Do

To maintain feasibility, the project intentionally excludes:

* Real‑time grid control
* Full AC power‑flow equations
* National or multi‑country grids
* High‑frequency real‑time simulation

These are beyond university‑scale resources.

---

## 9. Development Roadmap

### Phase 1: Research & Scoping

* Select region
* Gather data
* Define assumptions

### Phase 2: Core Simulation

* Demand model
* Supply model
* Storage model

### Phase 3: Reliability Modeling

* Stress tests
* Failure detection

### Phase 4: AI Optimization

* Objective formulation
* Scenario generation

### Phase 5: Visualization & UI

* Dashboard build
* Interactive controls

### Phase 6: Polish & Documentation

* Validation checks
* Demo scenarios

---

## 10. Validation & Limitations

This project provides **relative insights**, not absolute predictions.

Results should be interpreted as:

* Directional
* Comparative
* Scenario‑dependent

Limitations must be clearly stated in all presentations.

---

## 11. Who This Project Is For

* University students
* Energy policy researchers
* Municipal planners (exploratory use)
* Sustainability organizations

It is not intended for operational grid control.

---

## 12. Expected Deliverables

* Working interactive dashboard
* Multiple transition scenarios
* Written technical documentation
* Demo presentation or video

---

## 13. Final Notes

This project is intentionally designed to be:

* Ambitious but achievable
* Technically honest
* Policy‑relevant
* Educational

If built correctly, it demonstrates **systems thinking**, **AI literacy**, and **real‑world engineering judgment** — far more valuable than raw complexity.

---

**End of README**
