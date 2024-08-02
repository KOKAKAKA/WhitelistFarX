#!/bin/bash

# Path to your Node.js application
APP_PATH="/storage/emulated/0/Download/TermuxS/WhitelistFarX/whitelist.js"
# Path to the cache clear count file
COUNT_FILE="/storage/emulated/0/Download/TermuxS/WhitelistFarX/cacheClearCount.json"

# Function to start the server
start_server() {
    echo "Starting server..."
    node "$APP_PATH"
}

# Function to check cache clear count and restart server if needed
check_and_restart_server() {
    # Check if count file exists and read its contents
    if [ -f "$COUNT_FILE" ]; then
        local cacheClearCount
        cacheClearCount=$(jq '.count' "$COUNT_FILE")
        if [ "$cacheClearCount" -ge 3 ]; then
            echo "Cache cleared 3 times. Waiting 2 seconds before restarting."
            sleep 2
        fi
    fi
    start_server
}

# Loop to restart the server when it stops
while true; do
    check_and_restart_server
    echo "Server stopped. Restarting in 1 second..."
    sleep 1
done
