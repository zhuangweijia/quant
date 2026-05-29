#!/bin/bash
set -e

ENV_FILE="$(dirname "$0")/../.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "Creating .env from .env.example..."
    cp "$(dirname "$0")/../.env.example" "$ENV_FILE"
fi

generate_password() {
    openssl rand -hex 32
}

generate_fernet_key() {
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || \
    pip install -q cryptography && python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
}

update_env() {
    local key="$1"
    local value="$2"
    if grep -q "^${key}=" "$ENV_FILE"; then
        local tmp
        tmp=$(mktemp)
        awk -v k="$key" -v v="$value" 'BEGIN{FS=OFS="="} $1==k{$2=v; found=1} {print} END{if(!found) print k"="v}' "$ENV_FILE" > "$tmp" && mv "$tmp" "$ENV_FILE"
    else
        echo "${key}=${value}" >> "$ENV_FILE"
    fi
}

needs_replace() {
    local key="$1"
    local current
    current=$(grep "^${key}=" "$ENV_FILE" | cut -d'=' -f2-)
    [ -z "$current" ] || echo "$current" | grep -qi "CHANGE_ME\|example\|your-"
}

echo "Checking .env for placeholder values..."

if needs_replace POSTGRES_PASSWORD; then
    echo "  Generating POSTGRES_PASSWORD..."
    update_env POSTGRES_PASSWORD "$(generate_password)"
fi

if needs_replace ENCRYPTION_KEY; then
    echo "  Generating ENCRYPTION_KEY..."
    update_env ENCRYPTION_KEY "$(generate_fernet_key)"
fi

if needs_replace REDIS_PASSWORD; then
    echo "  Generating REDIS_PASSWORD..."
    update_env REDIS_PASSWORD "$(generate_password)"
fi

if needs_replace ADMIN_PASSWORD; then
    echo "  Generating ADMIN_PASSWORD..."
    update_env ADMIN_PASSWORD "$(generate_password | head -c 16)"
fi

current_cors=$(grep "^CORS_ORIGINS=" "$ENV_FILE" | cut -d'=' -f2-)
if echo "$current_cors" | grep -qi "your-domain\|example\|localhost" ; then
    server_ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -n "$server_ip" ]; then
        echo "  Setting CORS_ORIGINS to http://${server_ip}:3000..."
        update_env CORS_ORIGINS "http://${server_ip}:3000"
    fi
fi

if ! grep -q "^ADMIN_USERNAME=" "$ENV_FILE"; then
    update_env ADMIN_USERNAME "admin"
fi
if ! grep -q "^ADMIN_EMAIL=" "$ENV_FILE"; then
    update_env ADMIN_EMAIL "admin@quant.local"
fi
if ! grep -q "^NGINX_SSL_ENABLED=" "$ENV_FILE"; then
    update_env NGINX_SSL_ENABLED "false"
fi

echo ""
echo "Done! .env file is ready."
echo ""
echo "Generated credentials:"
echo "  ADMIN_USERNAME: $(grep '^ADMIN_USERNAME=' "$ENV_FILE" | cut -d'=' -f2-)"
echo "  ADMIN_PASSWORD: $(grep '^ADMIN_PASSWORD=' "$ENV_FILE" | cut -d'=' -f2-)"
echo ""
echo "Save these credentials - they will be needed to log in."
