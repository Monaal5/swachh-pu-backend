"""
Location router — endpoints for location, block, floor, and room lists.
"""

from fastapi import APIRouter, Depends
from app.models.location import (
    LocationListResponse,
    BlockListResponse,
    FloorListResponse,
    RoomListResponse,
)
from app.services import location_service

router = APIRouter(tags=["Locations & Hierarchy"])

@router.get("/locations", response_model=LocationListResponse)
async def get_locations():
    """
    Get all active campus locations.
    """
    return await location_service.get_locations()

@router.get("/locations/{location_id}/blocks", response_model=BlockListResponse)
async def get_blocks(location_id: int):
    """
    Get all building blocks under a specific location.
    """
    return await location_service.get_blocks_by_location(location_id)

@router.get("/blocks/{block_id}/floors", response_model=FloorListResponse)
async def get_floors(block_id: int):
    """
    Get all floors for a block, with their respective room count.
    """
    return await location_service.get_floors_by_block(block_id)

@router.get("/floors/{floor_id}/rooms", response_model=RoomListResponse)
async def get_rooms(floor_id: int):
    """
    Get all rooms under a specific floor.
    """
    return await location_service.get_rooms_by_floor(floor_id)
