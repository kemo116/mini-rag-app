#!/bin/sh
set -e

echo "Running mini-RAG app..."

cd /app/models/db_schemes/minirag/
alembic upgrade head
cd /app

exec "$@"
