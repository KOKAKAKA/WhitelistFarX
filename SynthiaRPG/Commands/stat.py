import discord
from discord.ext import commands
import json
import os

MAX_LEVEL = 100

def calculate_experience_needed(level):
    return 50 * level

class StatCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="stat", description="Shows your current stats with job boosts.")
    async def stat(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        stats_path = f'Asset/Player/{user_id}/PlayerId-Config.json'

        if not os.path.exists(stats_path):
            await interaction.response.send_message('You need to register first using `/register`.', ephemeral=True)
            return

        with open(stats_path, 'r') as f:
            player = json.load(f)

        current_level = player['level']
        current_experience = player['experience']
        experience_needed = calculate_experience_needed(current_level)
        experience_to_next_level = experience_needed - current_experience

        # Auto-level up if experience meets the requirement
        while current_experience >= experience_needed and current_level < MAX_LEVEL:
            current_experience -= experience_needed
            current_level += 1
            experience_needed = calculate_experience_needed(current_level)
            player['level'] = current_level
            player['experience'] = current_experience
            # Ensure stats do not exceed MAX_STAT
            for stat in ['health', 'mana', 'strength', 'agility', 'magic']:
                if player[stat] > MAX_STAT:
                    player[stat] = MAX_STAT

            with open(stats_path, 'w') as f:
                json.dump(player, f, indent=4)

        embed = discord.Embed(
            title='Player Stats',
            description=(
                f"Name: {player['name']}\n"
                f"Job: {player['job']}\n"
                f"Level: {player['level']}\n"
                f"Experience: {player['experience']} / {experience_needed}\n"
                f"Health: {player['health']}\n"
                f"Mana: {player['mana']}\n"
                f"Strength: {player['strength']}\n"
                f"Agility: {player['agility']}\n"
                f"Magic: {player['magic']}"
            ),
            color=discord.Color.random()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(StatCommand(bot))
