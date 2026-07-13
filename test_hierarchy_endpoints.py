import httpx

BASE_URL = "http://127.0.0.1:8000"

def test_hierarchy_endpoints():
    print("=== Testing Location Hierarchy API Endpoints ===")
    
    # 1. Test GET /locations
    r = httpx.get(f"{BASE_URL}/locations")
    print(f"GET /locations: Status {r.status_code} (Expected: 200)")
    assert r.status_code == 200
    data = r.json()
    assert "locations" in data
    locations = data["locations"]
    assert len(locations) > 0
    
    # Get the first location
    location = locations[0]
    assert "id" in location
    assert "name" in location
    loc_id = location["id"]
    print(f"Found location: {location['name']} (ID: {loc_id})")

    # 2. Test GET /locations/{location_id}/blocks
    r = httpx.get(f"{BASE_URL}/locations/{loc_id}/blocks")
    print(f"GET /locations/{loc_id}/blocks: Status {r.status_code} (Expected: 200)")
    assert r.status_code == 200
    data = r.json()
    assert "locationId" in data
    assert data["locationId"] == loc_id
    assert "blocks" in data
    blocks = data["blocks"]
    assert len(blocks) > 0
    
    # Get the first block
    block = blocks[0]
    assert "id" in block
    assert "name" in block
    block_id = block["id"]
    print(f"Found block: {block['name']} (ID: {block_id})")

    # 3. Test GET /blocks/{block_id}/floors
    r = httpx.get(f"{BASE_URL}/blocks/{block_id}/floors")
    print(f"GET /blocks/{block_id}/floors: Status {r.status_code} (Expected: 200)")
    assert r.status_code == 200
    data = r.json()
    assert "blockId" in data
    assert data["blockId"] == block_id
    assert "floors" in data
    floors = data["floors"]
    assert len(floors) > 0
    
    # Get the first floor
    floor = floors[0]
    assert "id" in floor
    assert "name" in floor
    assert "roomCount" in floor
    floor_id = floor["id"]
    print(f"Found floor: {floor['name']} (ID: {floor_id}), rooms: {floor['roomCount']}")

    # 4. Test GET /floors/{floor_id}/rooms
    r = httpx.get(f"{BASE_URL}/floors/{floor_id}/rooms")
    print(f"GET /floors/{floor_id}/rooms: Status {r.status_code} (Expected: 200)")
    assert r.status_code == 200
    data = r.json()
    assert "floorId" in data
    assert data["floorId"] == floor_id
    assert "rooms" in data
    rooms = data["rooms"]
    assert len(rooms) > 0
    
    # Get the first room
    room = rooms[0]
    assert "id" in room
    assert "name" in room
    assert "room_number" in room
    assert "room_name" in room
    print(f"Found room: {room['name']} (ID: {room['id']}), room_number: {room['room_number']}, room_name: {room['room_name']}")

    # 5. Test invalid IDs
    r = httpx.get(f"{BASE_URL}/locations/99999/blocks")
    assert r.status_code == 404
    r = httpx.get(f"{BASE_URL}/blocks/99999/floors")
    assert r.status_code == 404
    r = httpx.get(f"{BASE_URL}/floors/99999/rooms")
    assert r.status_code == 404
    print("Invalid ID checks passed!")

    print("All Hierarchy API endpoints verified successfully!\n")

if __name__ == "__main__":
    test_hierarchy_endpoints()
