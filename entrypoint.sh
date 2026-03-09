#!/bin/sh

# Set default values for environment variables
PORT=${PORT:-5050}
WORKERS=${GUNICORN_WORKERS:-4}

echo "Starting Gunicorn with $WORKERS workers on port $PORT..."

# Execute Gunicorn
# Using exec allows Gunicorn to be the main process (PID 1), which helps with signal handling
exec gunicorn -w "$WORKERS" -b "0.0.0.0:${PORT}" --timeout "120" "app:app"
