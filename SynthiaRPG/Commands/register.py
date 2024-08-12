import discord
from discord.ext import commands
import json
import os

class RegisterCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("RegisterCommand cog initialized")

    @discord.app_commands.command(name="register", description="Register a new player with a specified job.")
    async def register(self, interaction: discord.Interaction, name: str, job: str):
        print(f"Register command called with name: {name} and job: {job}")

        valid_jobs = ['Fighter', 'Tank', 'Archer', 'Magician']
        if job not in valid_jobs:
            await interaction.response.send_message(
                "Invalid job selected. Please choose from: Fighter, Tank, Archer, Magician.",
                ephemeral=True
            )
            return

        user_id = str(interaction.user.id)
        stats_path = f'Asset/Player/{user_id}/PlayerId-Config.json'

        if os.path.exists(stats_path):
            print("User already registered")
            await interaction.response.send_message(
                'You have already registered. Use `/stat` to view your stats.',
                ephemeral=True
            )
            return

        os.makedirs(os.path.dirname(stats_path), exist_ok=True)
        player = {
            'name': name,
            'money': 100,
            'experience': 0,
            'level': 1,
            'job': job,
            'health': 150 if job == 'Tank' else 100,
            'mana': 50,
            'strength': 30 if job == 'Fighter' else 20,
            'agility': 25 if job == 'Archer' else 15,
            'magic': 40 if job == 'Magician' else 10
        }

        with open(stats_path, 'w') as f:
            json.dump(player, f, indent=4)

        embed = discord.Embed(
            title='Player Registered',
            description=(
                f"**Name:** {name}\n"
                f"**Job:** {job}\n"
                f"**Money:** 100\n"
                f"**Experience:** 0\n"
                f"**Level:** 1\n"
                f"**Health:** {player['health']}\n"
                f"**Mana:** {player['mana']}\n"
                f"**Strength:** {player['strength']}\n"
                f"**Agility:** {player['agility']}\n"
                f"**Magic:** {player['magic']}"
            ),
            color=discord.Color.random()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RegisterCommand(bot))
    print("RegisterCommand cog loaded")
