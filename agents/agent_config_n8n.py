"""
CrewAI Agents Configuration - n8n Integration
Defines agents that use n8n webhooks for data access
"""
from crewai import Agent, Task, Crew
from crewai.tools import tool
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# n8n Webhook base URL
N8N_BASE_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook")


# Define n8n webhook tools as CrewAI tools
@tool
def get_region_snapshot_tool(region_name: str) -> dict:
    """
    Retrieves the most recent flight snapshot for a specified region from n8n.
    Use this to get current flight data including positions, altitudes, and speeds.
    
    Args:
        region_name: Name of the region to query (e.g., 'USA_East_Coast')
    """
    try:
        url = f"{N8N_BASE_URL}/mcp/flights/list_region_snapshot?region_name={region_name}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # EXTREME OPTIMIZATION: Minimal data to stay under 12k token limit
        # Even with 5 flights + alerts, we're hitting 14k tokens
        if isinstance(data, dict) and "flights" in data and isinstance(data["flights"], list):
            total_flights = len(data["flights"])
            
            # Return only SUMMARY, not individual flights
            # This reduces ~10k tokens to ~100 tokens
            summary = {
                "success": True,
                "region": region_name,
                "total_flights": total_flights,
                "timestamp": data.get("timestamp", "unknown"),
                "summary_note": f"Data summarized for token efficiency. {total_flights} flights detected in this region."
            }
            return summary
                
        return data
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_flight_by_callsign_tool(callsign: str) -> dict:
    """
    Finds and returns the latest data for a specific flight by its callsign or ICAO24 from n8n.
    Use this to track a specific flight.
    
    Args:
        callsign: Flight callsign (e.g., 'UAL123') or ICAO24 (e.g., '4baa1a')
    """
    try:
        url = f"{N8N_BASE_URL}/mcp/flights/get_by_callsign?callsign={callsign}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_active_alerts_tool(max_age_hours: int = 24) -> dict:
    """
    Returns all currently active anomaly alerts from n8n.
    Use this to check for flagged anomalies.
    
    Args:
        max_age_hours: Maximum age of alerts in hours (default: 24)
    """
    try:
        url = f"{N8N_BASE_URL}/mcp/alerts/list_active?max_age_hours={max_age_hours}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # EXTREME OPTIMIZATION: Return only counts, not full alerts
        if isinstance(data, dict) and "alerts" in data:
            alert_count = len(data.get("alerts", []))
            return {
                "success": True,
                "total_alerts": alert_count,
                "summary_note": f"Found {alert_count} active alerts in the last {max_age_hours} hours."
            }
        
        return data
    except Exception as e:
        return {"success": False, "error": str(e)}


# Create Ops Analyst Agent
def create_ops_analyst_agent():
    """Creates the Operations Analyst Agent that uses n8n webhooks"""
    return Agent(
        role="Airspace Operations Analyst",
        goal="Monitor regional airspace, detect anomalies, and provide actionable intelligence to operations teams",
        backstory="""You are an experienced air traffic analyst with 15 years of experience 
        monitoring commercial and private aviation. You have a keen eye for unusual patterns 
        and can quickly identify potential safety concerns. Your mission is to ensure safe 
        skies by detecting and reporting anomalies in real-time flight data.
        
        You use n8n webhooks to access live flight data managed by our workflow automation system.
        n8n handles:
        - Fetching data from OpenSky Network every 60 seconds
        - Detecting anomalies automatically
        - Storing snapshots and alerts
        
        When you query data, you're getting information directly from n8n's processed results,
        which includes anomaly detection already performed.""",
        verbose=True,
        allow_delegation=True,
        tools=[get_region_snapshot_tool, get_active_alerts_tool],
        llm="groq/llama-3.3-70b-versatile"
    )


# Create Traveler Support Agent
def create_traveler_support_agent():
    """Creates the Traveler Support Agent that uses n8n webhooks"""
    return Agent(
        role="Personal Flight Assistant",
        goal="Help travelers track their flights and answer questions about flight status with friendly, clear communication",
        backstory="""You are a helpful and knowledgeable flight assistant who loves helping 
        people track their journeys. You have access to real-time flight data managed by n8n,
        our workflow automation system.
        
        You excel at:
        - Finding specific flights by callsign or flight number
        - Explaining flight status in plain language
        - Providing reassurance and context about normal flight operations
        - Recognizing when to escalate concerns to the Ops Analyst
        
        When you retrieve flight data, it comes from n8n webhooks which are continuously 
        updated with the latest information from OpenSky Network. You communicate in a warm, 
        professional manner and always ground your responses in actual flight data.""",
        verbose=True,
        allow_delegation=True,
        tools=[get_flight_by_callsign_tool, get_region_snapshot_tool],
        llm="groq/llama-3.3-70b-versatile"
    )


# A2A Communication example: Traveler Support asks Ops Analyst
def create_multiagent_crew(ops_agent, traveler_agent):
    """Creates a crew with both agents for A2A communication"""
    return Crew(
        agents=[ops_agent, traveler_agent],
        verbose=True
    )


# Example tasks
def create_ops_analysis_task(agent, region_name: str):
    """Task for Ops Analyst to analyze a region"""
    return Task(
        description=f"""Analyze the airspace in {region_name} and provide a comprehensive summary.
        
        Steps:
        1. Retrieve the latest flight snapshot for {region_name} using n8n webhook
        2. Check the anomaly data already detected by n8n
        3. Query active alerts from n8n
        4. Generate a clear summary including:
           - Total number of flights
           - Number of anomalies detected
           - Description of the most critical cases
           - Recommended actions
        
        Remember: n8n has already performed anomaly detection, so you can focus on 
        interpreting the results and providing actionable intelligence.""",
        agent=agent,
        expected_output="A detailed natural-language summary of the region's airspace status with anomaly highlights"
    )


def create_traveler_query_task(agent, callsign: str, user_question: str):
    """Task for Traveler Support to answer user question"""
    return Task(
        description=f"""A traveler is asking about flight {callsign}: "{user_question}"
        
        Steps:
        1. Look up the latest data for flight {callsign} using n8n webhook
        2. Analyze the flight's current status (position, altitude, speed, direction)
        3. Answer the traveler's question in plain, friendly language
        4. If there are any concerns or anomalies, consider consulting the Ops Analyst
        
        Provide a helpful, reassuring response grounded in actual flight data from n8n.""",
        agent=agent,
        expected_output="A friendly, informative response to the traveler's question based on real flight data"
    )


if __name__ == "__main__":
    # Test agents
    print("Creating agents with n8n integration...")
    ops_agent = create_ops_analyst_agent()
    traveler_agent = create_traveler_support_agent()
    
    print("\n✅ Ops Analyst Agent created (using n8n webhooks)")
    print("✅ Traveler Support Agent created (using n8n webhooks)")
    
    # Test crew
    crew = create_multiagent_crew(ops_agent, traveler_agent)
    print("✅ Multi-agent crew configured with n8n integration")
