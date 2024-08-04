#!/bin/bash

# Directory to monitor
DIR_TO_MONITOR="/storage/emulated/0/download/TermuxS"

# Path to the last update timestamp file
TIMESTAMP_FILE="stamp.txt"

# Cooldown period in seconds (1 minute)
COOLDOWN_PERIOD=60

# Function to get the current timestamp
current_timestamp() {
    date +%s
}

# Create timestamp file if it does not exist
if [ ! -f "$TIMESTAMP_FILE" ]; then
    echo 0 > "$TIMESTAMP_FILE"
fi

# Get the last update timestamp
LAST_UPDATE=$(cat "$TIMESTAMP_FILE")

while true; do
    # Find files modified within the cooldown period
    FILES_MODIFIED=$(find "$DIR_TO_MONITOR" -type f -newermt "$(date -d @$LAST_UPDATE)" -print)
    
    if [ -n "$FILES_MODIFIED" ]; then
        echo "Files have been modified. Running update script..."
        
        # Your update logic here
        # Example: git pull, etc.
        git add .
        git commit -m "Updated $action $file"
        git push origin main
        # Update the last update timestamp
        echo "$(current_timestamp)" > "$TIMESTAMP_FILE"
    else
        echo "No files have been modified since the last check."
    fi
    
    # Sleep for a while before checking again
    sleep $COOLDOWN_PERIOD
done
