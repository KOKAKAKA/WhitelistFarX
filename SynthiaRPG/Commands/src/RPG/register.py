import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import json

class Register(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def save_player_data(self, player_id, data):
        with open(f'Commands/Asset/Player/{player_id}.json', 'w') as f:
            json.dump(data, f)

    def load_player_data(self, player_id):
        try:
            with open(f'Commands/Asset/Player/{player_id}.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    @commands.command()
    async def register(self, ctx, name: str):
        player_id = str(ctx.author.id)
        if self.load_player_data(player_id):
            await ctx.send(f'{ctx.author.mention}, you are already registered.')
            return

        jobs = {
            'fighter': {'health': 100, 'strength': 25, 'magic': 0, 'dexterity': 25},
            'tank': {'health': 150, 'strength': 15, 'magic': 0, 'dexterity': 20},
            'magician': {'health': 80, 'strength': 10, 'magic': 25, 'dexterity': 15},
            'archer': {'health': 90, 'strength': 20, 'magic': 0, 'dexterity': 30}
        }

        buttons = [
            Button(label='Fighter', style=discord.ButtonStyle.red, custom_id='fighter'),
            Button(label='Tank', style=discord.ButtonStyle.orange, custom_id='tank'),
            Button(label='Magician', style=discord.ButtonStyle.blue, custom_id='magician'),
            Button(label='Archer', style=discord.ButtonStyle.yellow, custom_id='archer')
        ]

        view = View()
        for button in buttons:
            view.add_item(button)

        async def button_callback(interaction):
            job = interaction.data['custom_id']
            player_data = {'name': name, 'job': job.capitalize(), 'level': 1, 'xp': 0, 'stat_points': 2, 'money': 0}
            player_data.update(jobs[job])
            self.save_player_data(player_id, player_data)
            await interaction.response.send_message(f'{ctx.author.mention}, you have registered as a {job.capitalize()}!')

        for button in view.children:
            button.callback = button_callback

        await ctx.send(f'{ctx.author.mention}, choose your job:', view=view)

def setup(bot):
    bot.add_cog(Register(bot))
