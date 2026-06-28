#!/bin/bash
set -e
if [ -f "config.env" ]; then
    export $(grep -v '^#' config.env | xargs)
fi
exec python3 -m Backend
