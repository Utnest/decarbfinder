import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

# Defining the main information

st.set_page_config(
    page_title="Energy Transition Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper function to generate sample scenario data
def generate_scenario_data(city, population, energy_old, energy_new):
    """Generate sample data for visualization - line chart format"""
    years = np.arange(2025, 2051)
    
    # Annual Demand (red line) - growing over time
    annual_demand = 100 + (years - 2025) * 3.5  # Linear growth
    
    # Energy Generated (yellow line) - starts lower, catches up and exceeds
    energy_generated = 80 + (years - 2025) * 4.2  # Slightly faster growth
    
    data = {
        'Year': years,
        'Annual Demand': annual_demand,
        'Energy Generated': energy_generated
    }
    
    return pd.DataFrame(data)

def create_line_chart(df, energy_old, energy_new):
    """Create simple line chart for Annual Demand vs Energy Generated"""
    fig = go.Figure()
    
    # Annual Demand line (red)
    fig.add_trace(go.Scatter(
        x=df['Year'], 
        y=df['Annual Demand'],
        name='Annual Demand',
        mode='lines+markers',
        line=dict(color='#E74C3C', width=3),
        marker=dict(size=8, color='#E74C3C')
    ))
    
    # Energy Generated line (yellow/green)
    fig.add_trace(go.Scatter(
        x=df['Year'], 
        y=df['Energy Generated'],
        name='Energy Generated',
        mode='lines+markers',
        line=dict(color='#F1C40F', width=3),
        marker=dict(size=8, color='#F1C40F')
    ))
    
    fig.update_layout(
        title=f'Energy Transition: {energy_old} → {energy_new}',
        xaxis_title='Year',
        yaxis_title='Energy (TWh)',
        hovermode='x unified',
        height=500,
        template='plotly_dark',
        plot_bgcolor='#2C3E50',
        paper_bgcolor='#34495E',
        font=dict(size=14),
        xaxis=dict(
            showgrid=True,
            gridcolor='#4A5F7F',
            dtick=5
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#4A5F7F'
        )
    )
    
    return fig

# Sidebar for user input 
with st.sidebar:
    st.header("📊 Scenario Configuration")

    # City Text Entry
    city = st.text_input(
        "City / Region",
        value="Toronto",
        placeholder="Enter city name",
        help="Enter the name of the city or region to model"
    )

    # Population Slider
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

    # Old Energy Source
    energy_old = st.selectbox(
        "Current Energy Source (to phase out)",
        ["Coal", "Natural Gas", "Fossil Fuels"],
        index=0,
        help="Carbon-based source to transition away from"
    )

    # New energy source
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
st.title("⚡ Energy Transition Simulator")
st.markdown("AI-Assisted Visual Decision-Support System for Clean Energy Planning")
st.markdown("---")

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

# Chart visualization
if 'scenarios_generated' in st.session_state and st.session_state['scenarios_generated']:
    
    # Generate data
    scenario_df = generate_scenario_data(city, population, energy_old, energy_new)
    
    # Display the line chart
    st.plotly_chart(
        create_line_chart(scenario_df, energy_old, energy_new),
        use_container_width=True
    )
    
    # Add download option
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col2:
        csv = scenario_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Data",
            data=csv,
            file_name=f'{city}_energy_scenario.csv',
            mime='text/csv'
        )
else:
    st.info("👈 Configure your scenario in the sidebar and click 'Generate Scenarios' to see the chart")