"""
Location service — database queries for locations, blocks, floors, and rooms.
"""

from collections import Counter
from fastapi import HTTPException, status
from app.utils.db import get_db
from app.models.location import (
    LocationInfo,
    LocationListResponse,
    BlockInfo,
    BlockListResponse,
    FloorInfo,
    FloorListResponse,
    RoomInfo,
    RoomListResponse,
)

async def get_locations() -> LocationListResponse:
    """Fetch all locations from the database."""
    admin = get_db()
    res = admin.table("locations").select("*").order("name").execute()
    
    locations = [LocationInfo(id=row["id"], name=row["name"]) for row in res.data]
    return LocationListResponse(locations=locations)

async def get_blocks_by_location(location_id: int) -> BlockListResponse:
    """Fetch all blocks under a specific location."""
    admin = get_db()
    
    # Check if location exists
    loc_check = admin.table("locations").select("id").eq("id", location_id).execute()
    if not loc_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {location_id} not found."
        )

    res = admin.table("blocks").select("*").eq("location_id", location_id).order("name").execute()
    
    blocks = [BlockInfo(id=row["id"], name=row["name"]) for row in res.data]
    return BlockListResponse(locationId=location_id, blocks=blocks)

async def get_floors_by_block(block_id: int) -> FloorListResponse:
    """Fetch all floors under a specific block and calculate room counts."""
    admin = get_db()
    
    # Check if block exists
    block_check = admin.table("blocks").select("id").eq("id", block_id).execute()
    if not block_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID {block_id} not found."
        )

    # Get floors
    floors_res = admin.table("floors").select("*").eq("block_id", block_id).order("name").execute()
    floors_data = floors_res.data
    
    if not floors_data:
        return FloorListResponse(blockId=block_id, floors=[])

    # Get all room counts for these floors to populate roomCount
    floor_ids = [f["id"] for f in floors_data]
    rooms_res = admin.table("rooms").select("id, floor_id").in_("floor_id", floor_ids).execute()
    
    # Count in python to avoid complex postgrest syntax issues
    counts = Counter(r["floor_id"] for r in rooms_res.data)
    
    floors = []
    for row in floors_data:
        floors.append(
            FloorInfo(
                id=row["id"],
                name=row["name"],
                roomCount=counts[row["id"]]
            )
        )
        
    return FloorListResponse(blockId=block_id, floors=floors)

async def get_rooms_by_floor(floor_id: int) -> RoomListResponse:
    """Fetch all rooms under a specific floor and resolve room display names."""
    admin = get_db()
    
    # Check if floor exists
    floor_check = admin.table("floors").select("id").eq("id", floor_id).execute()
    if not floor_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Floor with ID {floor_id} not found."
        )

    res = admin.table("rooms").select("*").eq("floor_id", floor_id).order("room_number").order("name").execute()
    
    rooms = []
    for row in res.data:
        room_number = row.get("room_number", "N/A")
        room_name = row.get("name", "")
        
        # Resolve display name: use room number if valid and not "N/A", else room name
        if room_number and room_number != "N/A":
            display_name = room_number
        else:
            display_name = room_name if room_name else "N/A"
            
        rooms.append(
            RoomInfo(
                id=row["id"],
                name=display_name,
                room_number=room_number,
                room_name=room_name
            )
        )
        
    return RoomListResponse(floorId=floor_id, rooms=rooms)
