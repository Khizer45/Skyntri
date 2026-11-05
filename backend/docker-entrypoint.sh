#!/bin/sh
set -e

# Apply database migrations before starting the API (SK-09).
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    alembic upgrade head
fi

exec "$@"
