# DungeonMaster: AI-powered TTRPG DM
# Python 3.11, embedded ChromaDB; mount data/ for vault
FROM python:3.11-slim

WORKDIR /app

# Application and config
COPY pyproject.toml requirements.txt .
COPY src/ src/
COPY config/ config/

# Install deps and package
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir .

# Default vault dir (mount over with volume); app reads VAULT_PATH
ENV VAULT_PATH=/data
RUN mkdir -p /data/systems /data/notes /data/characters /data/npcs /data/state /data/_index

# Run as non-root
RUN useradd -m dm && chown -R dm:dm /app /data
USER dm

ENTRYPOINT ["python", "-m", "dungeonmaster.main"]
