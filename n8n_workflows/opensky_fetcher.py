"""
OpenSky API Fetcher
Fetches flight data from OpenSky Network API and stores snapshots
"""
import requests
import time
import json
from datetime import datetime
from typing import Optional, Dict
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mcp_server.data_store import DataStore
# Import anomaly_detector module directly to avoid importing agent_config
import agents.anomaly_detector
AnomalyDetector = agents.anomaly_detector.AnomalyDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenSkyFetcher:
    """Fetches data from OpenSky Network API"""
    
    BASE_URL = "https://opensky-network.org/api/states/all"
    
    def __init__(self, data_store: DataStore):
        self.data_store = data_store
        self.detector = AnomalyDetector()
        logger.info("OpenSky Fetcher initialized")
    
    def fetch_region(self, region_name: str, bounding_box: Optional[Dict] = None) -> Dict:
        """
        Fetch flight data for a region
        
        Args:
            region_name: Name of the region
            bounding_box: Optional dict with keys: min_lat, max_lat, min_lon, max_lon
        
        Returns:
            Dictionary with flight data
        """
        try:
            # Build query parameters
            params = {}
            if bounding_box:
                params = {
                    "lamin": bounding_box.get("min_lat"),
                    "lomin": bounding_box.get("min_lon"),
                    "lamax": bounding_box.get("max_lat"),
                    "lomax": bounding_box.get("max_lon")
                }
            
            logger.info(f"Fetching data for {region_name} with params: {params}")
            
            # Make request
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            
            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("Rate limited by OpenSky API")
                return {
                    "success": False,
                    "error": "Rate limited",
                    "status_code": 429
                }
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Successfully fetched {len(data.get('states', []))} flights")
            
            # Save snapshot
            self.data_store.save_snapshot(region_name, data)
            
            # Detect anomalies
            flights = self._parse_flights(data)
            anomalies = self.detector.detect_anomalies(flights)
            
            # Save anomalies as alerts
            for anomaly in anomalies:
                alert_data = {
                    "region": region_name,
                    "callsign": anomaly["flight"].get("callsign"),
                    "icao24": anomaly["flight"].get("icao24"),
                    "anomaly_type": anomaly["anomaly_type"],
                    "severity": anomaly["severity"],
                    "description": anomaly["description"],
                    "flight_data": anomaly["flight"]
                }
                self.data_store.save_alert(alert_data)
            
            return {
                "success": True,
                "region": region_name,
                "timestamp": datetime.now().isoformat(),
                "total_flights": len(flights),
                "anomalies": len(anomalies)
            }
            
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            return {
                "success": False,
                "error": "Request timeout"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_flights(self, opensky_data: Dict) -> list:
        """Parse OpenSky response into structured flight list"""
        flights = []
        
        if "states" in opensky_data and opensky_data["states"]:
            for state in opensky_data["states"]:
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
        
        return flights
    
    def fetch_loop(self, region_configs: Dict, interval_seconds: int = 60):
        """
        Continuous fetch loop for multiple regions
        
        Args:
            region_configs: Dict mapping region names to bounding boxes
            interval_seconds: Fetch interval (minimum 10-15 seconds recommended)
        """
        logger.info(f"Starting fetch loop with {len(region_configs)} regions, interval: {interval_seconds}s")
        
        while True:
            for region_name, bounding_box in region_configs.items():
                result = self.fetch_region(region_name, bounding_box)
                
                if result["success"]:
                    logger.info(f"✅ {region_name}: {result['total_flights']} flights, {result['anomalies']} anomalies")
                else:
                    logger.error(f"❌ {region_name}: {result.get('error')}")
                
                # Small delay between regions to avoid rate limiting
                time.sleep(2)
            
            logger.info(f"Sleeping for {interval_seconds} seconds...")
            time.sleep(interval_seconds)


# Predefined regions (examples - can be customized)
EXAMPLE_REGIONS = {
    "USA_East_Coast": {
        "min_lat": 36.0,
        "max_lat": 42.0,
        "min_lon": -80.0,
        "max_lon": -70.0
    },
    "Europe_Central": {
        "min_lat": 48.0,
        "max_lat": 52.0,
        "min_lon": 2.0,
        "max_lon": 10.0
    },
    "Asia_Pacific": {
        "min_lat": 35.0,
        "max_lat": 40.0,
        "min_lon": 135.0,
        "max_lon": 145.0
    }
}


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    # Initialize
    data_store = DataStore()
    fetcher = OpenSkyFetcher(data_store)
    
    # Check if running in manual or loop mode
    if len(sys.argv) > 1 and sys.argv[1] == "loop":
        # Continuous loop mode
        interval = int(os.getenv("FETCH_INTERVAL", 60))
        fetcher.fetch_loop(EXAMPLE_REGIONS, interval)
    else:
        # Single fetch for testing
        print("Running single fetch test...")
        result = fetcher.fetch_region("test_region", EXAMPLE_REGIONS["USA_East_Coast"])
        print(json.dumps(result, indent=2))
