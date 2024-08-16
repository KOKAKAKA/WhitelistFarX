import discord
from discord.ext import commands
import random
import json

class Explore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_player_data(self, player_id):
        try:
            with open(f'Commands/Asset/Player/{player_id}.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def save_player_data(self, player_id, data):
        with open(f'Commands/Asset/Player/{player_id}.json', 'w') as f:
            json.dump(data, f)

    @commands.command()
    async def explore(self, ctx):
        player_id = str(ctx.author.id)
        player_data = self.load_player_data(player_id)

        if not player_data:
            await ctx.send(f'{ctx.author.mention}, you need to register first.')
            return

        encounter_chance = random.randint(1, 100)
        boss_encounter = random.randint(1, 100) <= 10  # 10% chance to encounter a boss
        exp_gain = 20 if boss_encounter else 10
        money_gain = random.randint(5, 20)
        item_drop = 'Rare Item' if boss_encounter else 'Common Item'

        player_data['xp'] += exp_gain
        player_data['money'] += money_gain
        # Handle item drop logic here, e.g., adding to player inventory

        self.save_player_data(player_id, player_data)

        combat_message = f'{ctx.author.mention} encountered a {"boss" if boss_encounter else "monster"} and gained {exp_gain} XP, {money_gain} coins, and found a {item_drop}!'
        await ctx.send(combat_message)

def setup(bot):
    bot.add_cog(Explore(bot))
