# Backend Optimizer (Technetium)

This is our highly optimized, correctness-tested backend implementation in Go, ready to handle heavy concurrent read and write workloads.

## How to Run

To run the complete service alongside its required databases (PostgreSQL and Redis), ensure Docker and Docker Compose are installed on your host system.

1. Navigate to the root directory of this repository where the `docker-compose.yml` resides.
2. Build and spin up the backend images in detached mode:
   ```bash
   docker-compose down -v
   docker-compose up -d --build
   ```

## Exposed Services & Ports

The required API gracefully exposes itself via port **8080** natively configured on the host.

- **API Server:** `http://localhost:8080/` or `http://0.0.0.0:8080/`
- All required endpoints from the specification are mapped dynamically (including `/auth`, `/user`, and `/posts`).

*(Note: The database initiates max-threaded limits and runs on a bridged Docker network. The system disables WAL syncs and sync-commits in Postgres to prioritize throughput).*
