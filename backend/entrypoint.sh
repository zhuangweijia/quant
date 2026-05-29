#!/bin/sh
set -e

if [ ! -f "$JWT_PRIVATE_KEY_PATH" ] || [ ! -f "$JWT_PUBLIC_KEY_PATH" ]; then
    echo "Generating RSA key pair for JWT..."
    mkdir -p "$(dirname "$JWT_PRIVATE_KEY_PATH")" "$(dirname "$JWT_PUBLIC_KEY_PATH")"
    openssl genrsa -out "$JWT_PRIVATE_KEY_PATH" 2048 2>/dev/null
    openssl rsa -in "$JWT_PRIVATE_KEY_PATH" -pubout -out "$JWT_PUBLIC_KEY_PATH" 2>/dev/null
    echo "JWT keys generated."
fi

alembic upgrade head

python scripts/init_admin.py

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
