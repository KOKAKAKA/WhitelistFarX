#!/bin/bash

# Directory to watch
WATCH_DIR="/storage/emulated/0/download/TermuxS"

# Git repository directory
REPO_DIR="/storage/emulated/0/download/TermuxS"

# Navigate to the repository directory
cd "$REPO_DIR" || exit

# Run the inotifywait command to watch for changes
inotifywait -m -r -e modify,create,delete "$WATCH_DIR" | while read -r path action file; do
    echo "Change detected: $action $file"

    # Add, commit, and push changes to GitHub
    git add "$WATCH_DIR"
    git commit -m "Automated commit for change: $action $file"
    git push origin main
done

