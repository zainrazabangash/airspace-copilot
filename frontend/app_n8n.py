"""
Streamlit Frontend - n8n Integration
Beautiful UI using n8n webhooks for data access
"""
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.agent_config_n8n import (
    create_ops_analyst_agent,
    create_traveler_support_agent,
    create_ops_analysis_task,
    create_traveler_query_task
)
from crewai import Crew

# Page config
st.set_page_config(
    page_title="✈️ Airspace Copilot",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (same as before)
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #2E5CFF 0%, #7B61FF 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .main-header h1 { color: white; margin: 0; font-size: 2.5rem; font-weight: 700; }
    .main-header p { color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 1.1rem; }
    [data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# n8n Webhook base URL
N8N_BASE_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook")


def check_n8n_status():
    """Check if n8n is running"""
    try:
        response = requests.get("http://localhost:5678", timeout=5)
        return True
    except:
        return False


def get_region_data(region_name):
    """Fetch region snapshot from n8n webhook"""
    try:
        url = f"{N8N_BASE_URL}/mcp/flights/list_region_snapshot?region_name={region_name}"
        print(f"🔍 CALLING: {url}")  # DEBUG
        response = requests.get(url, timeout=10)
        print(f"✅ STATUS: {response.status_code}")  # DEBUG
        response.raise_for_status()
        
        data = response.json()
        
        # DEBUGGING STRUCTURE
        print(f"🔍 DEBUG INFO:")
        print(f"• Type: {type(data)}")
        if isinstance(data, list):
            print(f"• List Length: {len(data)}")
            if len(data) > 0:
                print(f"• First Item Keys: {data[0].keys() if isinstance(data[0], dict) else 'Not a dict'}")
                data = data[0] # Try unwrapping
        elif isinstance(data, dict):
            print(f"• Keys: {list(data.keys())}")
        
        print(f"📊 FLIGHTS KEY: {data.get('total_flights', 'MISSING')}")
        return data
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")  # DEBUG
        return {"success": False, "error": str(e)}
def get_flight_data(callsign):
    """Fetch specific flight data from n8n webhook"""
    try:
        url = f"{N8N_BASE_URL}/mcp/flights/get_by_callsign?callsign={callsign}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_active_alerts():
    """Fetch active alerts from n8n webhook"""
    try:
        url = f"{N8N_BASE_URL}/mcp/alerts/list_active"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


# Header
st.markdown("""
<div class="main-header">
    <h1>✈️ Airspace Copilot</h1>
    <p>Real-Time Flight Monitoring with n8n Workflow Automation</p>
</div>
""", unsafe_allow_html=True)

# Check n8n status
n8n_status = check_n8n_status()
if not n8n_status:
    st.error("🔴 n8n is not running! Please start it with: `docker start n8n`")
    st.info("📖 See INSTALL.md for setup instructions")
else:
    st.success("🟢 n8n is running - Workflows active")

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/airplane-take-off.png", width=150)
    st.title("Navigation")
    
    mode = st.radio(
        "Select Mode:",
        ["👤 Traveler Mode", "📊 Operations Mode"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### System Status")
    
    if n8n_status:
        st.markdown("✅ n8n: **Running**")
        st.markdown("✅ Workflows: **Active**")
        st.markdown("✅ OpenSky API: **Connected**")
    else:
        st.markdown("❌ n8n: **Offline**")
    
    st.markdown("---")
    st.markdown("### n8n Workflows")
    st.markdown("""
    **Active:**
    - 🔄 Data Fetcher (every 60s)
    - 🔔 Anomaly Detection
    - 🌐 MCP Webhooks
    
    **Powered by:**
    - 🤖 CrewAI Agents
    - ⚡ Groq LLM
    - ✈️ OpenSky Network
    """)

# Main content
if "👤 Traveler" in mode:
    # TRAVELER MODE (same logic, but using n8n functions)
    st.header("👤 Personal Flight Watchdog")
    st.markdown("Track your flight powered by n8n workflow automation.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Flight Identifier")
        flight_id = st.text_input(
            "Enter Callsign or ICAO24 ID:",
            placeholder="e.g., UAL123 or 4baa1a"
        )
        flight_label = st.text_input(
            "Label (optional):",
            placeholder="e.g., My flight"
        )
    
    with col2:
        st.subheader("Quick Actions")
        if st.button("🔍 Track Flight", type="primary", width="stretch"):
            if flight_id:
                with st.spinner("Querying n8n..."):
                    flight_data = get_flight_data(flight_id)
                    
                    if flight_data.get("success"):
                        flight_info = flight_data["flight"]
                        st.session_state["tracked_flight"] = flight_info
                        st.session_state["flight_label"] = flight_label or flight_id
                        st.success(f"✅ Found via n8n: {flight_id}")
                    else:
                        st.error(f"❌ Not found: {flight_data.get('error')}")
            else:
                st.warning("Please enter a flight identifier")
    
    # Display tracked flight
    if "tracked_flight" in st.session_state:
        st.markdown("---")
        st.subheader(f"📍 Tracking: {st.session_state.get('flight_label', 'Flight')}")
        
        flight = st.session_state["tracked_flight"]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Altitude", f"{flight.get('altitude', 'N/A')} m")
        with col2:
            st.metric("Speed", f"{flight.get('velocity', 'N/A')} km/h")
        with col3:
            st.metric("Heading", f"{flight.get('heading', 'N/A')}°")
        with col4:
            status = "🟢 Airborne" if not flight.get('on_ground') else "🔴 On Ground"
            st.metric("Status", status)
        
        st.markdown("### Flight Details")
        details_col1, details_col2 = st.columns(2)
        
        with details_col1:
            st.markdown(f"**Callsign:** {flight.get('callsign', 'N/A')}")
            st.markdown(f"**ICAO24:** {flight.get('icao24', 'N/A')}")
            st.markdown(f"**Origin Country:** {flight.get('origin_country', 'N/A')}")
        
        with details_col2:
            st.markdown(f"**Latitude:** {flight.get('latitude', 'N/A')}")
            st.markdown(f"**Longitude:** {flight.get('longitude', 'N/A')}")
            st.markdown(f"**Vertical Rate:** {flight.get('vertical_rate', 'N/A')} m/s")
        
        st.info("ℹ️ Data provided by n8n workflow from OpenSky Network")
    
    # Chat interface
    st.markdown("---")
    st.subheader("💬 Ask Questions About Your Flight")
    
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    
    for message in st.session_state["chat_history"]:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            st.chat_message("assistant").write(message["content"])
    
    user_question = st.chat_input("Ask about your flight...")
    
    if user_question and flight_id:
        st.session_state["chat_history"].append({"role": "user", "content": user_question})
        st.chat_message("user").write(user_question)
        
        with st.chat_message("assistant"):
            with st.spinner("Agent thinking (via n8n data)..."):
                try:
                    traveler_agent = create_traveler_support_agent()
                    task = create_traveler_query_task(traveler_agent, flight_id, user_question)
                    crew = Crew(agents=[traveler_agent], tasks=[task], verbose=False)
                    
                    result = crew.kickoff()
                    response = str(result)
                    
                    st.write(response)
                    st.session_state["chat_history"].append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"Sorry, error: {str(e)}"
                    st.error(error_msg)
                    st.session_state["chat_history"].append({"role": "assistant", "content": error_msg})

else:
    # OPERATIONS MODE
    st.header("📊 Airspace Operations Copilot")
    st.markdown("Monitor regional airspace powered by n8n workflow automation.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        region_name = st.selectbox(
            "Select Region:",
            ["USA_East_Coast", "Europe_Central", "Asia_Pacific"],
            help="Regions monitored by n8n workflows"
        )
    
    with col2:
        st.markdown("### Actions")
        fetch_button = st.button("🔄 Fetch Latest", type="primary", width="stretch")
        auto_refresh = st.checkbox("Auto-refresh (60s)", value=False)
    
    if fetch_button or auto_refresh or "region_data" not in st.session_state:
        if region_name:
            with st.spinner(f"Querying n8n for {region_name}..."):
                region_data = get_region_data(region_name)
                st.session_state["region_data"] = region_data
                st.session_state["last_update"] = datetime.now()
    
    if "last_update" in st.session_state:
        st.caption(f"Last updated: {st.session_state['last_update'].strftime('%H:%M:%S')} (from n8n)")
    
    if "region_data" in st.session_state:
        data = st.session_state["region_data"]
        
        if data.get("success"):
            flights = data.get("flights", [])
            
            st.markdown("### Current Status")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Flights", len(flights))
            with col2:
                alerts_data = get_active_alerts()
                total_alerts = len(alerts_data.get("alerts", []))
                st.metric("Active Alerts", total_alerts)
            with col3:
                st.metric("Data Source", "n8n Workflow")
            
            st.markdown("### Flight List")
            
            if flights:
                df = pd.DataFrame(flights)
                display_cols = ["callsign", "altitude", "velocity", "heading", "origin_country"]
                df_display = df[display_cols].copy()
                df_display.columns = ["Callsign", "Altitude (m)", "Speed (km/h)", "Heading", "Country"]
                
                st.dataframe(df_display, use_container_width=True, height=400)
                
                st.markdown("---")
                st.subheader("🤖 AI Analysis (n8n Data)")
                
                if st.button("Generate Summary", type="secondary"):
                    with st.spinner("Ops Analyst analyzing n8n data..."):
                        try:
                            ops_agent = create_ops_analyst_agent()
                            task = create_ops_analysis_task(ops_agent, region_name)
                            crew = Crew(agents=[ops_agent], tasks=[task], verbose=False)
                            
                            result = crew.kickoff()
                            summary = str(result)
                            
                            st.success("✅ Analysis complete")
                            st.markdown(summary)
                            
                        except Exception as e:
                            st.error(f"Analysis failed: {str(e)}")
            else:
                st.info("No flights currently in this region.")
        else:
            st.error(f"Failed to fetch from n8n: {data.get('error')}")
    
    if auto_refresh:
        time.sleep(60)
        st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888;">
    Powered by <strong>n8n Workflow Automation</strong> | CrewAI Agents | Groq LLM | OpenSky Network
</div>
""", unsafe_allow_html=True)
