import json
import os
from datetime import datetime

def update_whitelist_file(user_id: int, key: str, expiration: str, reason: str, request_time: datetime):
    file_path = 'WhitelistedUser.json'
    users_data = {}

    # Ensure the file exists
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            json.dump(users_data, file, indent=4)
    else:
        try:
            with open(file_path, 'r') as file:
                users_data = json.load(file)
        except (IOError, json.JSONDecodeError) as e:
            print(f'Error loading WhitelistedUser.json: {e}')
            users_data = {}

    print(f"Current users_data before update: {users_data}")

    users_data[str(user_id)] = {
        'key': key,
        'expiration': expiration,
        'reason': reason,
        'created': request_time.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'status': 'Whitelisted'
    }

    try:
        # Write changes to the file
        with open(file_path, 'w') as file:
            json.dump(users_data, file, indent=4)
        print(f"Updated users_data: {users_data}")
    except IOError as e:
        print(f'Error writing WhitelistedUser.json: {e}')

# Test the function
update_whitelist_file(1018400148923101264, '3f71c9dc-bd44-4448-938f-f05d825ab365', 'Never', 'Not Specified', datetime.utcnow())
