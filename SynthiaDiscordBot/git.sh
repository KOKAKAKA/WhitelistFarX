#!/bin/bash

# Directory to monitor
DIR_TO_MONITOR="/storage/emulated/0/download/TermuxS"

# Cooldown period in seconds (1 second)
COOLDOWN_PERIOD=1

# Navigate to the monitored directory
cd "$DIR_TO_MONITOR" || { echo "Directory $DIR_TO_MONITOR not found"; exit 1; }

while true; do
    # Check if index.lock file exists
    if [ -f ".git/index.lock" ]; then
        echo "Git index.lock file exists. Skipping update..."
        sleep $COOLDOWN_PERIOD
        continue
    fi

    # Check for changes
    CHANGES=$(git status --porcelain)

    if [ -n "$CHANGES" ]; then
        echo "Changes detected. Running update script..."

        # Stage changes
        git add . > /dev/null 2>&1

        # Prepare the commit message with a summary of changes
        COMMIT_MESSAGE="Automated commit: Changes detected"
        git status --short | while read -r STATUS FILE; do
            COMMIT_MESSAGE+="\n- $STATUS $FILE"
        done

        # Debug output to verify commit message
        echo "Commit Message:"
        echo "$COMMIT_MESSAGE"

        # Commit and push changes
        git commit -m "$COMMIT_MESSAGE" > /dev/null 2>&1
        git push origin main > /dev/null 2>&1
    fi

    # Sleep for a while before checking again
    sleep $COOLDOWN_PERIOD
done
