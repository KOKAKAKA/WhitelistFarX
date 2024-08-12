import discord
from discord.ext import commands
import json
import time
import asyncio

# Initialize the bot with slash commands only
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=commands.when_mentioned_or("/"), intents=intents)

# Store the time when the bot starts running
bot.start_time = time.time()

# Load bot token from SavedToken.json
def load_token():
    with open('SavedToken.json', 'r') as f:
        data = json.load(f)
    return data['token']

# Custom Help Function with Pagination and Buttons
class HelpButton(discord.ui.View):
    def __init__(self, bot, interaction, command_list, commands_per_page=5):
        super().__init__(timeout=60)
        self.bot = bot
        self.interaction = interaction
        self.command_list = command_list
        self.commands_per_page = commands_per_page
        self.page = 1
        self.total_pages = (len(self.command_list) + self.commands_per_page - 1) // self.commands_per_page

    def get_embed(self):
        start = (self.page - 1) * self.commands_per_page
        end = start + self.commands_per_page
        commands_to_show = self.command_list[start:end]
        
        embed = discord.Embed(
            title=f'Help - Page {self.page}/{self.total_pages}',
            color=discord.Color.blurple()
        )

        for command in commands_to_show:
            embed.add_field(
                name=f"/{command.name}",
                value=command.description or "No description provided.",
                inline=False
            )

        embed.set_footer(text=f"Page {self.page}/{self.total_pages}")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.interaction.user

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.red)
    async def previous_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.page > 1:
            self.page -= 1
            await interaction.response.edit_message(embed=self.get_embed())

    @discord.ui.button(label="Next", style=discord.ButtonStyle.green)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.page < self.total_pages:
            self.page += 1
            await interaction.response.edit_message(embed=self.get_embed())

# Event: Bot is ready
@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync the slash commands with Discord
    print(f'Bot is online as {bot.user}')

# Built-in /runtime command: Shows the bot's uptime
@bot.tree.command(name="runtime", description="Displays the bot's uptime.")
async def runtime(interaction: discord.Interaction):
    current_time = time.time()
    uptime = current_time - bot.start_time
    uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime))
    embed = discord.Embed(title="Bot Uptime", description=f"Uptime: {uptime_str}", color=0x00FF00)
    await interaction.response.send_message(embed=embed)

# Built-in /ping command: Checks the bot's latency
@bot.tree.command(name="ping", description="Checks the bot's latency.")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)  # Convert to milliseconds
    embed = discord.Embed(title="Pong!", description=f"Latency: {latency}ms", color=0x00FF00)
    await interaction.response.send_message(embed=embed)

# Built-in /help command: Shows a list of all commands with pagination
@bot.tree.command(name="help", description="Displays a list of all commands.")
async def help_command(interaction: discord.Interaction):
    command_list = bot.tree.get_commands()
    if not command_list:
        await interaction.response.send_message("No commands available.", ephemeral=True)
        return

    view = HelpButton(bot, interaction, command_list)
    await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)

# Load and run the bot
async def main():
    await bot.start(load_token())

asyncio.run(main())
