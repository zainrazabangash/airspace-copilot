"""
MCP Tools
Exposes flight data and alerts as MCP tools for agents
"""
from typing import Dict, List, Optional
from .data_store import DataStore
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPTools:
    """MCP Tools for flight data access"""
    
    def __init__(self, data_store: DataStore):
        self.data_store = data_store
        logger.info("MCP Tools initialized")
    
    def list_region_snapshot(self, region_name: str) -> Dict:
        """
        Tool: flights.list_region_snapshot
        Returns the most recent snapshot for a given region
        
        Args:
            region_name: Name of the region (e.g., "region1", "region2")
        
        Returns:
            Dictionary containing flight states and metadata
        """
        logger.info(f"Tool called: list_region_snapshot(region_name={region_name})")
        
        snapshot = self.data_store.get_latest_snapshot(region_name)
        
        if not snapshot:
            return {
                "success": False,
                "error": f"No snapshot found for region: {region_name}",
                "region": region_name,
                "flights": []
            }
        
        # Parse and structure the data
        flights = []
        if "data" in snapshot and "states" in snapshot["data"]:
            for state in snapshot["data"]["states"]:
                if len(state) >= 12:
                    flight = {
                        "icao24": state[0],
                        "callsign": state[1].strip() if state[1] else None,
                        "origin_country": state[2],
                        "longitude": state[5],
                        "latitude": state[6],
                        "altitude": state[7],
                        "on_ground": state[8],
                        "velocity": state[9],
                        "heading": state[10],
                        "vertical_rate": state[11]
                    }
                    flights.append(flight)
        
        return {
            "success": True,
            "region": region_name,
            "timestamp": snapshot.get("timestamp"),
            "total_flights": len(flights),
            "flights": flights
        }
    
    def get_by_callsign(self, callsign: str) -> Dict:
        """
        Tool: flights.get_by_callsign
        Finds the latest record for a given flight callsign or ICAO24 ID
        
        Args:
            callsign: Flight callsign (e.g., "UAL123") or ICAO24 (e.g., "4baa1a")
        
        Returns:
            Dictionary with flight details or error
        """
        logger.info(f"Tool called: get_by_callsign(callsign={callsign})")
        
        # Try callsign first
        flight = self.data_store.get_flight_by_callsign(callsign)
        
        # If not found, try ICAO24
        if not flight:
            flight = self.data_store.get_flight_by_icao24(callsign)
        
        if not flight:
            return {
                "success": False,
                "error": f"Flight not found: {callsign}",
                "callsign": callsign
            }
        
        return {
            "success": True,
            "flight": flight
        }
    
    def list_active_alerts(self, max_age_hours: int = 24) -> Dict:
        """
        Tool: alerts.list_active
        Returns currently flagged anomalies
        
        Args:
            max_age_hours: Maximum age of alerts to retrieve (default: 24 hours)
        
        Returns:
            Dictionary containing list of active alerts
        """
        logger.info(f"Tool called: list_active_alerts(max_age_hours={max_age_hours})")
        
        alerts = self.data_store.get_active_alerts(max_age_hours)
        
        return {
            "success": True,
            "total_alerts": len(alerts),
            "alerts": alerts
        }


# Tool registry for MCP server
def get_tool_definitions() -> List[Dict]:
    """Returns tool definitions in MCP format"""
    return [
        {
            "name": "flights.list_region_snapshot",
            "description": "Returns the most recent flight snapshot for a specified region, including all current flights with their positions, altitudes, speeds, and headings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region_name": {
                        "type": "string",
                        "description": "Name of the region to query (e.g., 'region1', 'region2')"
                    }
                },
                "required": ["region_name"]
            }
        },
        {
            "name": "flights.get_by_callsign",
            "description": "Finds and returns the latest data for a specific flight by its callsign or ICAO24 identifier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "callsign": {
                        "type": "string",
                        "description": "Flight callsign (e.g., 'UAL123') or ICAO24 address (e.g., '4baa1a')"
                    }
                },
                "required": ["callsign"]
            }
        },
        {
            "name": "alerts.list_active",
            "description": "Returns all currently active anomaly alerts, including unusual flight patterns, speed anomalies, or altitude issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_age_hours": {
                        "type": "integer",
                        "description": "Maximum age of alerts to retrieve in hours (default: 24)",
                        "default": 24
                    }
                },
                "required": []
            }
        }
    ]


if __name__ == "__main__":
    # Test the tools
    store = DataStore()
    tools = MCPTools(store)
    
    # Test list_region_snapshot
    result = tools.list_region_snapshot("test_region")
    print(f"Region snapshot: {result}")
    
    # Test get_by_callsign
    result = tools.get_by_callsign("UAL123")
    print(f"Flight data: {result}")
    
    # Test list_active_alerts
    result = tools.list_active_alerts()
    print(f"Active alerts: {result}")
