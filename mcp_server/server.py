"""
MCP Server - FastAPI Application
Exposes flight data and alerts as MCP tools via HTTP endpoints
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
from dotenv import load_dotenv

from .data_store import DataStore
from .tools import MCPTools, get_tool_definitions

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Airspace Copilot MCP Server",
    description="Model Context Protocol server for flight data and alerts",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize data store and tools
data_store = DataStore(
    snapshots_dir=os.getenv("DATA_STORE_PATH", "./data/snapshots"),
    alerts_dir=os.getenv("ALERTS_STORE_PATH", "./data/alerts")
)
mcp_tools = MCPTools(data_store)


# Pydantic models for request/response
class RegionSnapshotRequest(BaseModel):
    region_name: str


class FlightCallsignRequest(BaseModel):
    callsign: str


class AlertsRequest(BaseModel):
    max_age_hours: Optional[int] = 24


# Root endpoint
@app.get("/")
async def root():
    """Health check and API info"""
    return {
        "service": "Airspace Copilot MCP Server",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "tools": "/tools",
            "region_snapshot": "/tools/flights/list_region_snapshot",
            "get_flight": "/tools/flights/get_by_callsign",
            "active_alerts": "/tools/alerts/list_active"
        }
    }


# MCP tool discovery endpoint
@app.get("/tools")
async def list_tools():
    """List all available MCP tools"""
    return {
        "tools": get_tool_definitions()
    }


# Tool endpoints
@app.post("/tools/flights/list_region_snapshot")
async def list_region_snapshot(request: RegionSnapshotRequest):
    """Get the most recent snapshot for a region"""
    try:
        result = mcp_tools.list_region_snapshot(request.region_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/flights/get_by_callsign")
async def get_by_callsign(request: FlightCallsignRequest):
    """Get flight data by callsign or ICAO24"""
    try:
        result = mcp_tools.get_by_callsign(request.callsign)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/alerts/list_active")
async def list_active_alerts(request: AlertsRequest):
    """Get active anomaly alerts"""
    try:
        result = mcp_tools.list_active_alerts(request.max_age_hours)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Convenience GET endpoints
@app.get("/tools/flights/list_region_snapshot/{region_name}")
async def get_region_snapshot(region_name: str):
    """GET version of region snapshot"""
    try:
        result = mcp_tools.list_region_snapshot(region_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/flights/get_by_callsign/{callsign}")
async def get_flight(callsign: str):
    """GET version of flight lookup"""
    try:
        result = mcp_tools.get_by_callsign(callsign)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/alerts/list_active")
async def get_active_alerts(max_age_hours: int = 24):
    """GET version of active alerts"""
    try:
        result = mcp_tools.list_active_alerts(max_age_hours)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "localhost")
    port = int(os.getenv("MCP_SERVER_PORT", 8000))
    
    print(f"🚀 Starting MCP Server on http://{host}:{port}")
    print(f"📖 API Documentation: http://{host}:{port}/docs")
    
    uvicorn.run(app, host=host, port=port, log_level="info")
