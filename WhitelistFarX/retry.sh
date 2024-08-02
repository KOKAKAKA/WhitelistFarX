#!/bin/bash

URL="http://localhost:18635/fetch-keys-hwids"
RETRIES=5
DELAY=2

for ((i=1; i<=RETRIES; i++)); do
  echo "Attempt $i of $RETRIES..."
  if curl -X GET "$URL"; then
    echo "Request succeeded!"
    exit 0
  else
    echo "Request failed. Retrying in $DELAY seconds..."
    sleep $DELAY
  fi
done

echo "Request failed after $RETRIES attempts."
exit 1
