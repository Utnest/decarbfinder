from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pipeline import PipelineInputs, PipelineResults, run_pipeline


def _scenario_label(city: str, energy_old: str, energy_new: str) -> str:
    base = city.strip() or "scenario"
    return f"{base}_{energy_old}_to_{energy_new}".replace(" ", "_").lower()


def _build_line_chart(supply_totals: pd.DataFrame, title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=supply_totals["year"],
            y=supply_totals["annual_demand_mwh"],
            name="Annual Demand",
            mode="lines+markers",
            line=dict(color="#E74C3C", width=3),
            marker=dict(size=7, color="#E74C3C"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=supply_totals["year"],
            y=supply_totals["energy_generated_mwh"],
            name="Energy Generated",
            mode="lines+markers",
            line=dict(color="#F1C40F", width=3),
            marker=dict(size=7, color="#F1C40F"),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Energy (MWh)",
        hovermode="x unified",
        height=500,
        template="plotly_dark",
        plot_bgcolor="#2C3E50",
        paper_bgcolor="#34495E",
        font=dict(size=14),
        xaxis=dict(showgrid=True, gridcolor="#4A5F7F", dtick=5),
        yaxis=dict(showgrid=True, gridcolor="#4A5F7F"),
    )
    return fig


def _display_metrics(results: PipelineResults) -> None:
    supply_totals = results.supply_totals
    latest_year = int(supply_totals["year"].max())
    latest = supply_totals[supply_totals["year"] == latest_year].iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Base Year", int(results.metadata["base_year"]))
    with col2:
        st.metric("CAGR", f"{results.metadata['cagr'] * 100:.2f}%")
    with col3:
        st.metric(f"{latest_year} Demand (MWh)", f"{latest['annual_demand_mwh']:,.0f}")
    with col4:
        st.metric(f"{latest_year} Unmet (MWh)", f"{latest['unmet_demand_mwh']:,.0f}")


def _download_buttons(data_dir: Path) -> None:
    col1, col2, col3 = st.columns(3)
    with col1:
        with (data_dir / "module2_supply_outputs.csv").open("r") as f:
            st.download_button(
                "Download Supply Detail",
                data=f.read(),
                file_name="module2_supply_outputs.csv",
                mime="text/csv",
            )
    with col2:
        with (data_dir / "module3_storage_outputs.csv").open("r") as f:
            st.download_button(
                "Download Storage Results",
                data=f.read(),
                file_name="module3_storage_outputs.csv",
                mime="text/csv",
            )
    with col3:
        with (data_dir / "module5_optimizer_outputs.csv").open("r") as f:
            st.download_button(
                "Download Optimizer Results",
                data=f.read(),
                file_name="module5_optimizer_outputs.csv",
                mime="text/csv",
            )


def main() -> None:
    st.set_page_config(
        page_title="Energy Transition Simulator",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("⚡ Energy Transition Simulator")
    st.markdown("AI-Assisted Visual Decision-Support System for Clean Energy Planning")
    st.markdown("---")

    with st.sidebar:
        st.header("📊 Scenario Configuration")
        city = st.text_input(
            "City / Region",
            value="Toronto",
            placeholder="Enter city name",
            help="Enter the name of the city or region to model",
        )
        population = st.slider(
            "Population (Hundreds of Thousands)",
            min_value=1,
            max_value=1000,
            value=100,
            step=1,
            help="Used as a multiplier relative to the baseline demand data.",
        )
        st.subheader("⚡ Energy Sources")
        energy_old = st.selectbox(
            "Current Energy Source (to phase out)",
            ["Coal", "Natural Gas", "Fossil Fuels"],
            index=1,
            help="Carbon-based source to transition away from",
        )
        energy_new = st.selectbox(
            "New Energy Source",
            ["Hydro", "Solar", "Wind"],
            index=1,
            help="Clean energy source for the transition",
        )

        with st.expander("Advanced assumptions"):
            population_growth = st.slider(
                "Annual Population Growth",
                min_value=0.0,
                max_value=0.03,
                value=0.003,
                step=0.001,
                format="%.3f",
            )
            electrification_uplift = st.slider(
                "Annual Electrification Uplift",
                min_value=0.0,
                max_value=0.03,
                value=0.005,
                step=0.001,
                format="%.3f",
            )
            reserve_margin = st.slider(
                "Reserve Margin",
                min_value=0.0,
                max_value=0.3,
                value=0.15,
                step=0.01,
                format="%.2f",
            )

        scenario_name = st.text_input(
            "Scenario Label",
            value=_scenario_label(city, energy_old, energy_new),
            help="Used to label the scenario in exported results.",
        )

        if st.button("🚀 Generate Scenarios", type="primary", use_container_width=True):
            inputs = PipelineInputs(
                scenario_name=scenario_name,
                population_multiplier=population / 100.0,
                population_growth=population_growth,
                electrification_uplift=electrification_uplift,
                reserve_margin=reserve_margin,
                energy_old=energy_old,
                energy_new=energy_new,
            )
            base_dir = Path(__file__).resolve().parent
            with st.spinner("Running demand, supply, storage, and optimization modules..."):
                results = run_pipeline(base_dir, inputs)
            st.session_state["pipeline_results"] = results
            st.session_state["pipeline_inputs"] = asdict(inputs)
            st.success("✅ Scenarios generated successfully!")

    results: PipelineResults | None = st.session_state.get("pipeline_results")

    st.subheader("Selected Configuration")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("City", city if city else "Not specified")
    with col2:
        st.metric("Population", f"{population * 100_000:,}")
    with col3:
        st.metric("Old Source", energy_old)
    with col4:
        st.metric("New Source", energy_new)

    st.markdown("---")

    if results is None:
        st.info("👈 Configure your scenario in the sidebar and click 'Generate Scenarios' to run the full pipeline")
        return

    _display_metrics(results)

    st.plotly_chart(
        _build_line_chart(
            results.supply_totals,
            title=f"Energy Transition: {energy_old} → {energy_new}",
        ),
        use_container_width=True,
    )

    st.markdown("---")
    st.subheader("Storage & Reliability")
    st.dataframe(
        results.storage_results[[
            "year",
            "scenario",
            "storage_delivered_mwh",
            "unmet_demand_mwh",
            "reserve_margin",
            "reliability_pass",
        ]],
        use_container_width=True,
    )

    st.markdown("---")
    st.subheader("Optimizer Recommendations")
    st.dataframe(
        results.optimizer_results[[
            "weight_set",
            "scenario",
            "rank",
            "score",
            "total_cost",
            "total_emissions_t",
            "reliability_ok",
            "explanation",
        ]],
        use_container_width=True,
    )

    st.markdown("---")
    _download_buttons(Path(__file__).resolve().parent / "data")


if __name__ == "__main__":
    main()
