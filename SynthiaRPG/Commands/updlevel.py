import json
import os

def generate_level_config(max_level, multiplier):
    level_config = {}
    for level in range(1, max_level + 1):
        level_config[str(level)] = level * multiplier

    config_path = 'Asset/LevelConfig.json'
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(level_config, f, indent=4)

# Generate the level config with max level 100 and experience multiplier 50
generate_level_config(100, 50)
