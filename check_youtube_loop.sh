#!/bin/bash

# Function to check if YouTube main activity is running
check_youtube() {
  if am stack list | grep -q "com.google.android.youtube"; then
    echo "$(date): YouTube main activity is running."
  else
    echo "$(date): YouTube main activity is not running."
  fi
}

# Loop to check every 5 seconds
while true; do
  check_youtube
  sleep 5
done
