import json

class LevelSystem:
    def __init__(self, player_id):
        self.player_id = player_id
        self.player_data = self.load_player_data()

    def load_player_data(self):
        try:
            with open(f'Commands/Asset/Player/{self.player_id}.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def save_player_data(self):
        with open(f'Commands/Asset/Player/{self.player_id}.json', 'w') as f:
            json.dump(self.player_data, f)

    def check_level_up(self):
        level_threshold = 50 * self.player_data['level']
        if self.player_data['xp'] >= level_threshold:
            self.player_data['level'] += 1
            self.player_data['xp'] -= level_threshold
            self.player_data['stat_points'] += 2
            self.save_player_data()
            return True
        return False

# This function can be called in other scripts to check and apply level-up logic.
def level_up(player_id):
    level_system = LevelSystem(player_id)
    return level_system.check_level_up()
