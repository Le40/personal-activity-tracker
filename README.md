# Personal Activity Tracker

A lightweight, locally running activity tracker built with Python and FastAPI.

## Features (V1)

- Start and stop activities
- Automatically finish the previous activity when starting another
- Categorize activities by type
- View daily activity history and durations
- Persist data locally using SQLite

## Tech Stack

- Python 3.14
- FastAPI
- SQLAlchemy 2.x
- SQLite
- pytest

## Getting Started

### 1. Create a virtual environment

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 3. Run the application

```powershell
uvicorn main:app --reload
```

API documentation: http://127.0.0.1:8000/docs

## Status

Under development.