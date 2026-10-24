FROM python:3.14-slim

WORKDIR /code

# Install dependencies first to benefit from Docker's build cache.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source.
COPY app ./app
COPY init_db.py .

EXPOSE 8000

# Initialize SQLite and start FastAPI.
CMD ["sh", "-c", "python init_db.py && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]