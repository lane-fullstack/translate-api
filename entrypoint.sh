#!/bin/sh

# Get the number of CPU cores
CORES=$(nproc)

# Calculate the default number of workers based on Gunicorn's recommendation
DEFAULT_WORKERS=$((2 * CORES + 1))

# Use the GUNICORN_WORKERS environment variable if set, otherwise use the default
WORKERS=${GUNICORN_WORKERS:-$DEFAULT_WORKERS}

echo "Starting Gunicorn with $WORKERS workers..."

# Execute Gunicorn
# Using exec allows Gunicorn to be the main process (PID 1), which helps with signal handling
exec gunicorn -w "$WORKERS" -b "0.0.0.0:5050" --timeout "120" "app:app"
