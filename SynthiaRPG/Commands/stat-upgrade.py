class UpdateStatCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="update-stat", description="Upgrade your stats after leveling up.")
    async def update_stat(self, interaction: discord.Interaction, stat: str, amount: int):
        user_id = str(interaction.user.id)
        stats_path = f'Asset/Player/{user_id}/PlayerId-Config.json'

        if not os.path.exists(stats_path):
            await interaction.response.send_message('You need to register first using `/register`.', ephemeral=True)
            return

        with open(stats_path, 'r') as f:
            player = json.load(f)

        if player['stat_points'] < amount or amount < 0:
            await interaction.response.send_message(f"Invalid amount. You have {player['stat_points']} points to use.", ephemeral=True)
            return

        if stat in ['health', 'mana', 'strength', 'agility', 'magic'] and player[stat] + amount <= 200:
            player[stat] += amount
            player['stat_points'] -= amount
        else:
            await interaction.response.send_message("Invalid stat or stat already maxed.", ephemeral=True)
            return

        with open(stats_path, 'w') as f:
            json.dump(player, f, indent=4)

        embed = discord.Embed(
            title='Stat Updated',
            description=f"{stat.capitalize()} increased by {amount}.",
            color=discord.Color.random()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(UpdateStatCommand(bot))
