import os
import json
from datetime import datetime

def update_whitelist_file(user_id, key, expiration, reason, created):
    file_path = 'WhitelistedUser.json'
    
    # Check if the file exists and is not empty
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            with open(file_path, 'r') as file:
                users_data = json.load(file)
                print(f"Current users_data before update: {users_data}")
        except json.JSONDecodeError:
            print("Error loading WhitelistedUser.json: Invalid JSON format. Initializing as an empty JSON object.")
            users_data = {}
    else:
        print("WhitelistedUser.json does not exist or is empty. Initializing as an empty JSON object.")
        users_data = {}

    # Update the user's data
    users_data[user_id] = {
        'key': key,
        'expiration': expiration,
        'reason': reason,
        'created': created.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'status': 'Whitelisted'
    }
    
    # Write the updated data back to the file
    with open(file_path, 'w') as file:
        json.dump(users_data, file, indent=4)
    
    print(f"Updated users_data: {users_data}")
    
    # Verify the file contents after update
    with open(file_path, 'r') as file:
        updated_data = json.load(file)
        print(f"WhitelistedUser.json contents: {updated_data}")

# Usage
user_id = '1018400148923101264'
key = 'd2e6273f-fa87-49a7-b319-5069d9c7c3a1'
expiration = 'Never'
reason = 'Not Specified'
created = datetime.utcnow()

update_whitelist_file(user_id, key, expiration, reason, created)
