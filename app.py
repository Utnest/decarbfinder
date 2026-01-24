import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# Defining the main information

st.set_page_config(
    page_title = "Energy Transition Simulator",
    page_icon = "⚡",
    layout = "wide",
    initial_sidebar_state = "expanded"
)

#Sidebar for user input 
with st.sidebar:
    st.header("📊 Scenario Configuration")

    # City Text Entry
    city = st.text_input(
        "City / Region",
        value="Toronto",
        placeholder="Enter city name",
        help="Enter the name of the city or region to model"
    )

    # Population Slider (fixed type issue)
    population = st.slider(
        "Population (Hundreds of Thousands)",
        min_value=1,
        max_value=1000,
        value=100,
        step=1,
        help="Select the population in hundreds of thousands."
    )

    # Energy Sources Dropdowns
    st.subheader("⚡ Energy Sources")

    # Old Energy Source (single selection)
    energy_old = st.selectbox(
        "Current Energy Source (to phase out)",
        ["Coal", "Natural Gas", "Fossil Fuels"],
        index=0,
        help="Carbon-based source to transition away from"
    )

    # New energy source (single selection)
    energy_new = st.selectbox(
        "New Energy Source",
        ["Hydro", "Solar", "Wind"],
        index=1,
        help="Clean energy source for the transition"
    )

    st.markdown("---")
    
    # Generate scenarios button
    if st.button("🚀 Generate Scenarios", type="primary", use_container_width=True):
        st.session_state['scenarios_generated'] = True
        st.success("✅ Scenarios generated successfully!")

# Main content area
st.subheader("Selected Configuration")

# Display user selections
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("City", city if city else "Not specified")

with col2:
    # Convert to full number format with commas
    full_population = population * 100_000
    st.metric("Population", f"{full_population:,}")

with col3:
    st.metric("Old Source", energy_old if energy_old else "Not specified")

with col4:
    st.metric("New Source", energy_new if energy_new else "Not specified")

st.markdown("---")

# Placeholder for your charts and visualizations
st.info("Charts and analysis will appear here after generating scenarios")