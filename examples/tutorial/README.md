# AIORP Tutorial Example

This is a tutorial example demonstrating the usage of
AIORP (Async I/O Reverse Proxy) to create a proxy service that handles
authentication, compression, and routing for multiple microservices.

## Project Structure

```text
.
├── proxy/
│   ├── src/
│   │   ├── routers/
│   │   │   ├── inventory_router.py
│   │   │   └── transactions_router.py
│   │   ├── utils/
│   │   │   ├── auth.py
│   │   │   └── compression.py
│   │   └── app.py
│   └── pyproject.toml
└── targets/
```

## Set-up

1. Download the example
2. Open three shells
3. In the first one run:

   ```bash
   # Install uv if you haven't already
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Change dir to proxy
   cd proxy

   # Create virtualenv and install deps
   uv venv
   uv sync

   # Enter environment
   source .venv/bin/activate

   # Start proxy
   python3 -m src.app
   ```

4. In the second one:

   ```bash
   # Change dir to targets
   cd targets

   # Create virtualenv and install deps
   uv venv
   uv sync

   # Enter environment
   source .venv/bin/activate

   # Start transactions (detached) and inventory service
   python3 transactions.py & python3 inventory.py
   ```

The proxy will be available at `http://localhost:8080`

## API Endpoints

### Authentication

- `POST /login` - Authenticate and get JWT token

### Transactions Service

- All routes under `/transactions/*` are proxied to the transactions service
- Requires valid JWT token in Authorization header
- Shop making the request must match the shop_id in the URL

### Inventory Service

- All routes under `/shops/{shop_id}/inventory/*` are proxied to the inventory service
- Requires valid JWT token in Authorization header
- Shop making the request must match the shop_id in the URL

## Testing

1. First, obtain a JWT token:

   ```bash
   curl -X POST http://localhost:8080/login \
     -H "Content-Type: application/json" \
     -d '{"username": "BBY001", "password": "bby001"}'
   ```

2. Use the token to access protected endpoints:

   ```bash
   # Access transactions
   curl http://localhost:8080/shops/BBY001/transactions \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiQkJZMDAxIiwiZXhwIjoxNzQ2MTMwNTIwLCJpYXQiOjE3NDYxMjY5MjB9.t29ibFMpsNoHfQI4WcZFg-Yxw8VdddwfJOkOzvZ-fpI"

   # Access inventory
   curl http://localhost:8080/shops/BBY001/inventory \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
   ```

## Features

- JWT-based authentication
- Request compression
- Service-specific API key handling
- Shop-based access control for inventory and transactions
- Automatic request/response proxying

## Configuration

The proxy service uses the following configuration:

- Proxy service: `http://localhost:8080`
- Transactions service: `http://localhost:8001`
- Inventory service: `http://localhost:8002`

API keys and other sensitive information should be moved to environment
variables or a secure configuration system in a production environment.
