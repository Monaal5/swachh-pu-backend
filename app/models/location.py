"""
Pydantic schemas for Location Hierarchy endpoints.
"""

from typing import Optional
from pydantic import BaseModel, Field

class LocationInfo(BaseModel):
    """Details of a location."""
    id: int
    name: str

class LocationListResponse(BaseModel):
    """List of locations."""
    locations: list[LocationInfo]

class BlockInfo(BaseModel):
    """Details of a block."""
    id: int
    name: str

class BlockListResponse(BaseModel):
    """List of blocks for a location."""
    locationId: int = Field(..., alias="locationId")
    blocks: list[BlockInfo]

    model_config = {
        "populate_by_name": True
    }

class FloorInfo(BaseModel):
    """Details of a floor, including the number of rooms."""
    id: int
    name: str
    roomCount: int = Field(..., alias="roomCount")

    model_config = {
        "populate_by_name": True
    }

class FloorListResponse(BaseModel):
    """List of floors for a block."""
    blockId: int = Field(..., alias="blockId")
    floors: list[FloorInfo]

    model_config = {
        "populate_by_name": True
    }

class RoomInfo(BaseModel):
    """Details of a room."""
    id: int
    name: str = Field(..., description="Display name of the room (e.g. room number or descriptive name)")
    room_number: str = Field(..., description="Actual room number, or 'N/A'")
    room_name: str = Field(..., description="Description/name of the room")

class RoomListResponse(BaseModel):
    """List of rooms for a floor."""
    floorId: int = Field(..., alias="floorId")
    rooms: list[RoomInfo]

    model_config = {
        "populate_by_name": True
    }
