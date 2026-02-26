# Just change this line
FROM python:3.12-slim

WORKDIR /app

# Install libpq-dev for psycopg2-binary stability
RUN apt-get update && apt-get install -y libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "App.main:app", "--host", "0.0.0.0", "--port", "8000"]