#!/bin/bash
set -e

CONFIG_FILE="config.env"

if [ -f "$CONFIG_FILE" ]; then
    export $(grep -v '^#' "$CONFIG_FILE" | xargs)
fi

python3 -m Backend
