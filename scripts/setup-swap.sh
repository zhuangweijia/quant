#!/bin/bash
set -e

if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Use: sudo bash $0"
    exit 1
fi

SWAP_SIZE="${SWAP_SIZE:-2G}"
SWAP_FILE="${SWAP_FILE:-/swapfile}"

if swapon --show | grep -q "$SWAP_FILE"; then
    echo "Swap already active at $SWAP_FILE"
    swapon --show
    exit 0
fi

if [ -f "$SWAP_FILE" ]; then
    echo "Swap file exists but not active. Enabling..."
else
    echo "Creating ${SWAP_SIZE} swap file at ${SWAP_FILE}..."
    fallocate -l "$SWAP_SIZE" "$SWAP_FILE"
fi

chmod 600 "$SWAP_FILE"
mkswap "$SWAP_FILE" >/dev/null
swapon "$SWAP_FILE"

sysctl vm.swappiness=10

if ! grep -q "$SWAP_FILE" /etc/fstab; then
    echo "$SWAP_FILE none swap sw 0 0" >> /etc/fstab
    echo "Added to /etc/fstab for persistence."
fi

echo "Swap configured successfully:"
swapon --show
free -h
