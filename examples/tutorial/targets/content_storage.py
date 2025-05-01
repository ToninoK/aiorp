import json
from functools import wraps

from aiohttp import web

app = web.Application()

# API key for inventory service
INVENTORY_API_KEY = "inventory-secret-key-456"

# Load initial inventory from JSON file
with open("./example_inventory.json", "r") as f:
    inventory = json.load(f)["inventory"]


def require_api_key(handler):
    @wraps(handler)
    async def wrapper(request):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != INVENTORY_API_KEY:
            return web.json_response(
                {"error": "Invalid or missing API key"}, status=401
            )
        return await handler(request)

    return wrapper


@require_api_key
async def create_item(request):
    """Create a new inventory item"""
    shop_id = request.match_info["shop_id"]
    data = await request.json()
    item = {
        "id": len(inventory) + 1,
        "name": data["name"],
        "category": data["category"],  # produce/hardware/clothes
        "quantity": data["quantity"],
        "unit_price": data["unit_price"],
        "shop_id": shop_id,
        "shop_name": data["shop_name"],
        "supplier": data.get("supplier", ""),
        "last_restocked": data.get("last_restocked"),
        "minimum_stock": data.get("minimum_stock", 0),
    }
    inventory.append(item)
    return web.json_response(item, status=201)


@require_api_key
async def get_all_items(request):
    """Get all inventory items for a specific shop"""
    shop_id = request.match_info["shop_id"]
    filtered_items = [item for item in inventory if item["shop_id"] == shop_id]
    return web.json_response(filtered_items)


@require_api_key
async def get_item(request):
    """Get a specific item by ID for a specific shop"""
    shop_id = request.match_info["shop_id"]
    item_id = int(request.match_info["id"])
    item = next(
        (i for i in inventory if i["id"] == item_id and i["shop_id"] == shop_id), None
    )
    if item is None:
        return web.json_response({"error": "Item not found"}, status=404)
    return web.json_response(item)


@require_api_key
async def update_item(request):
    """Update a specific inventory item for a specific shop"""
    shop_id = request.match_info["shop_id"]
    item_id = int(request.match_info["id"])
    data = await request.json()

    item = next(
        (i for i in inventory if i["id"] == item_id and i["shop_id"] == shop_id), None
    )
    if item is None:
        return web.json_response({"error": "Item not found"}, status=404)

    item.update(
        {
            "name": data.get("name", item["name"]),
            "category": data.get("category", item["category"]),
            "quantity": data.get("quantity", item["quantity"]),
            "unit_price": data.get("unit_price", item["unit_price"]),
            "shop_id": shop_id,
            "shop_name": data.get("shop_name", item["shop_name"]),
            "supplier": data.get("supplier", item["supplier"]),
            "last_restocked": data.get("last_restocked", item["last_restocked"]),
            "minimum_stock": data.get("minimum_stock", item["minimum_stock"]),
        }
    )
    return web.json_response(item)


@require_api_key
async def delete_item(request):
    """Delete a specific inventory item for a specific shop"""
    shop_id = request.match_info["shop_id"]
    item_id = int(request.match_info["id"])
    item = next(
        (i for i in inventory if i["id"] == item_id and i["shop_id"] == shop_id), None
    )
    if item is None:
        return web.json_response({"error": "Item not found"}, status=404)

    inventory.remove(item)
    return web.json_response({"message": "Item deleted"})


# Setup routes
app.router.add_post("/shops/{shop_id}/inventory", create_item)
app.router.add_get("/shops/{shop_id}/inventory", get_all_items)
app.router.add_get("/shops/{shop_id}/inventory/{id}", get_item)
app.router.add_put("/shops/{shop_id}/inventory/{id}", update_item)
app.router.add_delete("/shops/{shop_id}/inventory/{id}", delete_item)

web.run_app(app, host="localhost", port=8002)
