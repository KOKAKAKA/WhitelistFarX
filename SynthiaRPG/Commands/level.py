import json
import os

def load_level_config():
    with open('Asset/LevelConfig.json', 'r') as f:
        return json.load(f)

def check_level_up(player):
    level_config = load_level_config()
    level = player['level']
    experience = player['experience']

    while experience >= level_config[str(level)] and level < 100:
        experience -= level_config[str(level)]
        level += 1

        if level < 100:
            player['level'] = level
            player['experience'] = experience
            player['stat_points'] += 6  # Points to distribute when leveling up
        else:
            player['experience'] = level_config[str(level)]  # Cap experience at max level

    return player
