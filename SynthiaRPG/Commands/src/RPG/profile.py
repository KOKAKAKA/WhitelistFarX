import discord
from discord.ext import commands
import json

class Profile(commands.Cog):
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
    async def profile(self, ctx):
        player_id = str(ctx.author.id)
        player_data = self.load_player_data(player_id)

        if not player_data:
            await ctx.send(f'{ctx.author.mention}, you need to register first.')
            return

        embed = discord.Embed(title=f'{player_data["name"]}\'s Profile', color=discord.Color.green())
        embed.add_field(name='Job', value=player_data['job'])
        embed.add_field(name='Level', value=player_data['level'])
        embed.add_field(name='XP', value=player_data['xp'])
        embed.add_field(name='Money', value=player_data['money'])
        embed.add_field(name='Health', value=player_data['health'])
        embed.add_field(name='Strength', value=player_data['strength'])
        embed.add_field(name='Magic', value=player_data['magic'])
        embed.add_field(name='Dexterity', value=player_data['dexterity'])

        upgrade_button = Button(label='Upgrade Stat', style=discord.ButtonStyle.primary)
        view = View()
        view.add_item(upgrade_button)

        async def upgrade_callback(interaction):
            stat_buttons = [
                Button(label='Health', style=discord.ButtonStyle.red, custom_id='health'),
                Button(label='Strength', style=discord.ButtonStyle.green, custom_id='strength'),
                Button(label='Magic', style=discord.ButtonStyle.blue, custom_id='magic'),
                Button(label='Dexterity', style=discord.ButtonStyle.yellow, custom_id='dexterity')
            ]

            stat_view = View()
            for button in stat_buttons:
                stat_view.add_item(button)

            async def stat_upgrade(interaction):
                stat = interaction.data['custom_id']
                if player_data['stat_points'] > 0:
                    player_data[stat] += {'health': 50, 'strength': 10, 'magic': 10, 'dexterity': 5}[stat]
                    player_data['stat_points'] -= 1
                    self.save_player_data(player_id, player_data)
                    await interaction.response.send_message(f'{stat.capitalize()} upgraded!')
                else:
                    await interaction.response.send_message('No stat points available.')

            for button in stat_view.children:
                button.callback = stat_upgrade

            await interaction.response.edit_message(content='Select a stat to upgrade:', view=stat_view)

        upgrade_button.callback = upgrade_callback

        await ctx.send(embed=embed, view=view)

def setup(bot):
    bot.add_cog(Profile(bot))
