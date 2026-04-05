# Load Testing with Locust

This folder contains a Locust script to generate high request volume against the backend API.

## What this test covers

- By default: `GET /health` and `GET /health-redis`.
- Optional authenticated flow (disabled by default): register/login + create/details/delete post over authenticated routes.

## 1) Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r loadtest/requirements.txt
```

## 2) Start backend

Run your backend using `docker-compose` to ensure all components (API, DB, Redis) are correctly wired and the DB is properly initialized.

```bash
docker-compose up -d --build
```
Ensure your server is reachable at `http://localhost:8080`.

## 3) Quick smoke run (headless)

Run a smaller test run to make sure nothing crashes in the environment:

```bash
locust -f loadtest/locustfile.py --host http://localhost:8080 --headless -u 20 -r 5 -t 30s
```

## 4) Heavy load run example

To really stretch what the APIs and underlying connections can process setup something like:

```bash
locust -f loadtest/locustfile.py --host http://localhost:8080 --headless -u 3000 -r 100 -t 10m --csv loadtest/results
```

## 5) Running the Authenticated API flow

You must explicitly export `ENABLE_AUTH_FLOW=true` for Locust to hit all the endpoints (Post create, read, delete, User queries). Make sure backend endpoints are un-commented.

```bash
ENABLE_AUTH_FLOW=true locust -f loadtest/locustfile.py --host http://localhost:8080 --headless -u 100 -r 10 -t 30s
```

Or you can use the web interface. Omit the `--headless` flags and navigate to `http://localhost:8089`:

```bash
ENABLE_AUTH_FLOW=true locust -f loadtest/locustfile.py
```
