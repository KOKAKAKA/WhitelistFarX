import discord
from discord.ext import commands
import json
import os
import random
import asyncio

class ExploreCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="explore", description="Explore the world and encounter random enemies.")
    async def explore(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        stats_path = f'Asset/Player/{user_id}/PlayerId-Config.json'

        if not os.path.exists(stats_path):
            await interaction.response.send_message('You need to register first using `/register`.', ephemeral=True)
            return

        enemies = [
            {"name": "Goblin", "health": 50, "attack": 10, "reward_exp": 20, "reward_money": (5, 10)},
            {"name": "Wolf", "health": 80, "attack": 15, "reward_exp": 30, "reward_money": (10, 20)},
            {"name": "Orc", "health": 120, "attack": 20, "reward_exp": 50, "reward_money": (20, 40)},
            {"name": "Dragon", "health": 200, "attack": 35, "reward_exp": 100, "reward_money": (50, 100)}  # Boss
        ]

        encounter = random.choice(enemies)
        player = self.load_player_data(stats_path)

        embed = discord.Embed(
            title=f"You encountered a {encounter['name']}!",
            description="What will you do?",
            color=discord.Color.red()
        )
        view = ExploreButton(self.bot, player, encounter, stats_path)
        await interaction.response.send_message(embed=embed, view=view)

    def load_player_data(self, stats_path):
        with open(stats_path, 'r') as f:
            return json.load(f)

class ExploreButton(discord.ui.View):
    def __init__(self, bot, player, encounter, stats_path):
        super().__init__(timeout=60)
        self.bot = bot
        self.player = player
        self.encounter = encounter
        self.stats_path = stats_path

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.red)
    async def attack_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        result = self.player_attack(interaction.user, self.encounter, self.player['strength'])
        await interaction.response.edit_message(embed=result, view=None)

    @discord.ui.button(label="Spell", style=discord.ButtonStyle.blurple)
    async def spell_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        result = self.player_attack(interaction.user, self.encounter, self.player['magic'])
        await interaction.response.edit_message(embed=result, view=None)

    @discord.ui.button(label="Run", style=discord.ButtonStyle.gray)
    async def run_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        success_chance = min(90, self.player['agility'] + random.randint(0, 50))
        if random.randint(0, 100) < success_chance:
            result = discord.Embed(
                title="Run Successful!",
                description="You managed to escape safely.",
                color=discord.Color.green()
            )
        else:
            result = discord.Embed(
                title="Run Failed!",
                description="The enemy caught up to you!",
                color=discord.Color.red()
            )
        await interaction.response.edit_message(embed=result, view=None)

    def player_attack(self, user, enemy, attack_stat):
        enemy['health'] -= attack_stat
        if enemy['health'] <= 0:
            return self.enemy_defeated(user, enemy)
        else:
            player_damage = max(0, enemy['attack'] - random.randint(0, 10))
            self.player['health'] -= player_damage

            if self.player['health'] <= 0:
                return self.player_defeated(user)
            else:
                embed = discord.Embed(
                    title=f"Attack Successful! {enemy['name']} Health: {enemy['health']}",
                    description=f"You dealt {attack_stat} damage and received {player_damage} damage.",
                    color=discord.Color.orange()
                )
                return embed

    def enemy_defeated(self, user, enemy):
        exp_gained = enemy['reward_exp']
        money_gained = random.randint(*enemy['reward_money'])
        self.player['experience'] += exp_gained
        self.player['money'] += money_gained

        embed = discord.Embed(
            title=f"{enemy['name']} defeated!",
            description=f"You gained {exp_gained} EXP and {money_gained} money.",
            color=discord.Color.gold()
        )

        self.update_level(user)
        self.save_player_data()
        return embed

    def player_defeated(self, user):
        embed = discord.Embed(
            title="You have been defeated!",
            description="Better luck next time.",
            color=discord.Color.red()
        )
        return embed

    def update_level(self, user):
        with open('Asset/LevelConfig.json', 'r') as f:
            level_config = json.load(f)

        current_level = self.player['level']
        while self.player['experience'] >= level_config[str(current_level)]:
            self.player['experience'] -= level_config[str(current_level)]
            self.player['level'] += 1
            current_level += 1

        embed = discord.Embed(
            title="Level Up!",
            description=f"Congratulations {user.name}, you reached level {self.player['level']}!",
            color=discord.Color.green()
        )

    def save_player_data(self):
        with open(self.stats_path, 'w') as f:
            json.dump(self.player, f, indent=4)

async def setup(bot):
    await bot.add_cog(ExploreCommand(bot))
