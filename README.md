# PATRICK — Personal Activity Tracker

[![Python Tests](https://github.com/Le40/personal-activity-tracker/actions/workflows/tests.yml/badge.svg)](https://github.com/Le40/personal-activity-tracker/actions/workflows/tests.yml)

A small, local activity tracker for recording how you actually spend your day. Start an activity, switch to another, and review your history in a compact window.

Built as a practical Python/FastAPI backend portfolio project, with a deliberately simple architecture and no account or cloud service required.


## Features

- **Track time:** Start and stop activities with a live timer. Starting another activity automatically finishes the previous one.
- **Review history:** Browse completed activities by day, with start/end times and durations.
- **Correct your records:** Add past activities manually, or edit and delete existing entries. Overlapping time intervals are rejected.
- **Add context:** Optional names and notes, with an effort/ease rating (1–5) for Work activities.
- **Keep it local:** Activity data is stored in SQLite. No sign-in or internet connection is needed for normal use.

Activity types: Work, Exercise, Meal, Break, Sleep, and Other. For reporting, a day runs from **05:00 to 05:00** in the **Europe/Bratislava** timezone.

## Run PATRICK

### Option 1 — Portable Windows executable (easiest)

1. Download `PAT.exe` from the [GitHub Releases page](https://github.com/Le40/personal-activity-tracker/releases) once a release is available.
2. Put it in a writable folder and double-click it.
3. PATRICK opens in a small **Microsoft Edge** app window.

On first launch, the application creates its SQLite database alongside the executable:

```text
PATRICK/
├── PAT.exe
└── activity_tracker.db
```

Keep `activity_tracker.db` when updating or moving the application: **that file contains your activity history**. Close PATRICK before copying it for backup. Microsoft Edge is required for this launcher; Python and Docker are not.

### Option 2 — Docker

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) or another Docker environment with Compose.

From the repository root:

```bash
docker compose up --build -d
```

Open **http://localhost:8001**. To stop PATRICK:

```bash
docker compose down
```

Docker stores its data in a **persistent named volume**, separate from the Windows executable's database. `docker compose down` preserves that volume; `docker compose down -v` deletes it.

### Option 3 — Run from source

Requires **Python 3.14**.

On Windows (PowerShell), from the repository root:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python launcher.py
```

`launcher.py` creates the database tables if needed, starts FastAPI, and opens the compact Edge window.

To run the API directly, without the Windows launcher:

```powershell
python init_db.py
python -m uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000** for the UI, or **http://127.0.0.1:8000/docs** for interactive API documentation.

## Architecture

```text
Vue 3 UI (served as static files, no build step)
              ↓ HTTP
          FastAPI
              ↓
    Activity business rules
              ↓
         SQLAlchemy
              ↓
            SQLite
```

**Backend:** Python 3.14, FastAPI, Pydantic, SQLAlchemy, SQLite.  
**Frontend:** Vue 3, HTML, CSS, JavaScript; served locally by FastAPI.  
**Quality:** pytest, Ruff, GitHub Actions.  
**Packaging:** Docker Compose and PyInstaller for Windows.

The API enforces a single running activity, validates timestamps and activity types, and prevents overlapping completed activities. SQLite keeps the project lightweight and suitable for a single local user.

### Example API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/activities/current` | Get the running activity |
| `POST` | `/activities/start` | Start an activity (automatically stops the previous one) |
| `POST` | `/activities/stop` | Stop the running activity |
| `GET` | `/activities?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` | Retrieve completed activity history |
| `POST` | `/activities` | Add a completed activity |
| `PUT` | `/activities/{id}` | Update an activity |
| `DELETE` | `/activities/{id}` | Delete an activity |
| `GET` | `/activities/options` | List activity types and ratings |

The complete interactive API reference is available at `/docs` while the server is running.

## Development and tests

Install the development requirements, then run:

```powershell
python -m pytest -q
python -m ruff check .
```

Tests cover activity lifecycle, input validation, time overlaps, history queries, and API behavior. GitHub Actions runs the test suite on pushes and pull requests.

## Scope

PATRICK is intentionally a **single-user, local-first utility**. It does not provide authentication, synchronization, automatic activity detection, or AI-based recommendations. The priority is reliable manual tracking and straightforward, maintainable backend code.

## License

No license has been specified yet. See the repository for any future licensing terms.
