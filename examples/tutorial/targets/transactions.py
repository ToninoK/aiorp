import json
from functools import wraps

from aiohttp import web

app = web.Application()

# API key for transactions service
TRANSACTIONS_API_KEY = "transactions-secret-key-123"

# Load initial transactions from JSON file
with open("./example_transactions.json", "r") as f:
    transactions = json.load(f)["transactions"]


def require_api_key(handler):
    @wraps(handler)
    async def wrapper(request):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != TRANSACTIONS_API_KEY:
            return web.json_response(
                {"error": "Invalid or missing API key"}, status=401
            )
        return await handler(request)

    return wrapper


@require_api_key
async def create_transaction(request):
    """Create a new transaction"""
    shop_id = request.match_info["shop_id"]
    data = await request.json()
    transaction = {
        "id": len(transactions) + 1,
        "shop_name": data["shop_name"],
        "shop_id": shop_id,
        "category": data["category"],  # grocery/tech/clothes
        "amount": data["amount"],
        "description": data["description"],
        "date": data["date"],
    }
    transactions.append(transaction)
    return web.json_response(transaction, status=201)


@require_api_key
async def get_all_transactions(request):
    """Get all transactions for a specific shop"""
    shop_id = request.match_info["shop_id"]
    filtered_transactions = [t for t in transactions if t["shop_id"] == shop_id]
    return web.json_response(filtered_transactions)


@require_api_key
async def get_transaction(request):
    """Get a specific transaction by ID for a specific shop"""
    shop_id = request.match_info["shop_id"]
    transaction_id = int(request.match_info["id"])
    transaction = next(
        (
            t
            for t in transactions
            if t["id"] == transaction_id and t["shop_id"] == shop_id
        ),
        None,
    )
    if transaction is None:
        return web.json_response({"error": "Transaction not found"}, status=404)
    return web.json_response(transaction)


@require_api_key
async def update_transaction(request):
    """Update a specific transaction for a specific shop"""
    shop_id = request.match_info["shop_id"]
    transaction_id = int(request.match_info["id"])
    data = await request.json()

    transaction = next(
        (
            t
            for t in transactions
            if t["id"] == transaction_id and t["shop_id"] == shop_id
        ),
        None,
    )
    if transaction is None:
        return web.json_response({"error": "Transaction not found"}, status=404)

    transaction.update(
        {
            "shop_name": data.get("shop_name", transaction["shop_name"]),
            "shop_id": shop_id,
            "category": data.get("category", transaction["category"]),
            "amount": data.get("amount", transaction["amount"]),
            "description": data.get("description", transaction["description"]),
            "date": data.get("date", transaction["date"]),
        }
    )
    return web.json_response(transaction)


@require_api_key
async def delete_transaction(request):
    """Delete a specific transaction for a specific shop"""
    shop_id = request.match_info["shop_id"]
    transaction_id = int(request.match_info["id"])
    transaction = next(
        (
            t
            for t in transactions
            if t["id"] == transaction_id and t["shop_id"] == shop_id
        ),
        None,
    )
    if transaction is None:
        return web.json_response({"error": "Transaction not found"}, status=404)

    transactions.remove(transaction)
    return web.json_response({"message": "Transaction deleted"})


# Setup routes
app.router.add_post("/shops/{shop_id}/transactions", create_transaction)
app.router.add_get("/shops/{shop_id}/transactions", get_all_transactions)
app.router.add_get("/shops/{shop_id}/transactions/{id}", get_transaction)
app.router.add_put("/shops/{shop_id}/transactions/{id}", update_transaction)
app.router.add_delete("/shops/{shop_id}/transactions/{id}", delete_transaction)

web.run_app(app, host="localhost", port=8001)
