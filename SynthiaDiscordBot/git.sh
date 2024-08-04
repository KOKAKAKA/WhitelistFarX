#!/bin/bash

# Directory to monitor (should be the git repository root or include path to the repo)
DIR_TO_MONITOR="/storage/emulated/0/download/TermuxS"

# Path to the last update timestamp file
TIMESTAMP_FILE="$DIR_TO_MONITOR/stamp.txt"

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

# Navigate to the monitored directory
cd "$DIR_TO_MONITOR" || { echo "Directory $DIR_TO_MONITOR not found"; exit 1; }

while true; do
    # Find files modified within the cooldown period
    FILES_MODIFIED=$(find . -type f -newermt "$(date -d @$LAST_UPDATE)" -print)

    if [ -n "$FILES_MODIFIED" ]; then
        echo "Files have been modified. Running update script..."

        # Add files to git staging area
        git add .

        # Prepare the commit message with a list of modified files
        COMMIT_MESSAGE="Automated commit: Files modified:"
        for FILE in $FILES_MODIFIED; do
            COMMIT_MESSAGE+="\n- $FILE"
        done

        # Commit and push changes
        git commit -m "$COMMIT_MESSAGE"
        git push origin main

        # Update the last update timestamp
        echo "$(current_timestamp)" > "$TIMESTAMP_FILE"
    else
        echo "No files have been modified since the last check."
    fi

    # Sleep for a while before checking again
    sleep $COOLDOWN_PERIOD
done
