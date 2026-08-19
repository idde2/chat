FROM python:3.11-slim

WORKDIR /app

# Systemvoraussetzungen installieren
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || pip install flask flask-socketio mysql-connector-python pyjwt bcrypt

COPY . .

EXPOSE 5000

CMD ["python", "main.py"]
