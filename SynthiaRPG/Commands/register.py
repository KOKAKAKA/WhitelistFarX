import discord
from discord.ext import commands
import json
import os

class RegisterCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="register", description="Register a new player.")
    async def register(self, interaction: discord.Interaction, name: str):
        # Define job buttons
        class JobSelectionView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)

            @discord.ui.button(label="Fighter", style=discord.ButtonStyle.red)
            async def fighter_button(self, button: discord.ui.Button, interaction: discord.Interaction):
                await self.register_job(interaction, 'Fighter')

            @discord.ui.button(label="Tank", style=discord.ButtonStyle.orange)
            async def tank_button(self, button: discord.ui.Button, interaction: discord.Interaction):
                await self.register_job(interaction, 'Tank')

            @discord.ui.button(label="Archer", style=discord.ButtonStyle.secondary)
            async def archer_button(self, button: discord.ui.Button, interaction: discord.Interaction):
                await self.register_job(interaction, 'Archer')

            @discord.ui.button(label="Magician", style=discord.ButtonStyle.blurple)
            async def magician_button(self, button: discord.ui.Button, interaction: discord.Interaction):
                await self.register_job(interaction, 'Magician')

            async def register_job(self, interaction: discord.Interaction, job: str):
                user_id = str(interaction.user.id)
                stats_path = f'Asset/Player/{user_id}/PlayerId-Config.json'

                if os.path.exists(stats_path):
                    await interaction.response.send_message('You have already registered. Use `/stat` to view your stats.', ephemeral=True)
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
                    description=f"Name: {name}\nJob: {job}\nMoney: 100\nExperience: 0\nLevel: 1",
                    color=discord.Color.random()
                )
                await interaction.response.edit_message(embed=embed, view=None)

        # Initial message with job selection
        view = JobSelectionView()
        embed = discord.Embed(
            title='Select Your Job',
            description='Choose your job by clicking one of the buttons below.',
            color=discord.Color.random()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RegisterCommand(bot))
