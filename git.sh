#!/bin/bash

# Change to your repository directory
cd /storage/emulated/0/download/TermuxS

# Check for changes
if [[ `git status --porcelain` ]]; then
  # Add changes to staging
  git add .

  # Commit with a timestamped message
  git commit -m "Update $(date '+%Y-%m-%d %H:%M:%S')"

  # Push to the remote repository
  git push origin main
fi
