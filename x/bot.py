import logging
import discord
from discord.ext import commands
import json
import re
import aiohttp

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load the token from token.json
try:
    with open('token.json') as f:
        data = json.load(f)
        TOKEN = data['token']
except (FileNotFoundError, KeyError):
    print("Error: token.json file not found or token key missing.")
    exit()

# Define the bot with Intents
intents = discord.Intents.default()
intents.message_content = True  # Required for reading message content
bot = commands.Bot(command_prefix='!', intents=intents)

# Slash command with a modal input
class BypassModal(discord.ui.Modal, title="Bypass Input"):
    bypass_input = discord.ui.TextInput(
        label="Enter your link",
        placeholder="Paste the link here...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_input = str(self.bypass_input.value).strip()

        # Check which service is being used and format the API request accordingly
        fluxus_pattern = r"https://flux\.li/android/external/start\.php\?HWID=([a-f0-9]+)"
        arceus_x_pattern = r"https://spdmteam\.com/.+"

        # Acknowledge the interaction immediately to prevent timeout
        await interaction.response.defer(ephemeral=True)

        if match := re.match(fluxus_pattern, user_input):
            hwid = match.group(1)
            api_url = f"https://stickx.top/api-fluxus/?hwid={hwid}&api_key=E99l9NOctud3vmu6bPne"
            service = "Fluxus"
        elif re.match(arceus_x_pattern, user_input):
            hwid = user_input  # For Arceus X, the whole link is used as HWID
            api_url = f"https://stickx.top/api-arceusx/?hwid={hwid}&api_key=tUnAZj3sS74DJo9BUb8tshpVhpLJLA"
            service = "Arceus X"
        else:
            embed = discord.Embed(
                title="Error",
                description="Unsupported link or format. Please check your input.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Make the API request
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    # Check for success and extract the key
                    if data.get('Status') == 'Success' and 'key' in data:
                        key = data['key']
                        embed = discord.Embed(
                            title=f"{service} Bypass Successful",
                            description=f"**Key:** `{key}`",
                            color=discord.Color.green()
                        )
                    else:
                        embed = discord.Embed(
                            title=f"Failed to bypass {service}",
                            description="Unexpected response format.",
                            color=discord.Color.red()
                        )
                else:
                    embed = discord.Embed(
                        title=f"Failed to bypass {service}",
                        description=f"Error: {response.status}",
                        color=discord.Color.red()
                    )

                await interaction.followup.send(embed=embed, ephemeral=True)

# Define the /bypass command with the new description
@bot.tree.command(name="bypass", description="Bypass A Link")
async def bypass(interaction: discord.Interaction):
    modal = BypassModal()
    await interaction.response.send_modal(modal)

# Define the /supported-link command
@bot.tree.command(name="supported-link", description="Shows the supported links")
async def supported_link(interaction: discord.Interaction):
    supported_links = (
        "Supported links:\n"
        "- Fluxus: `https://flux.li/android/external/start.php?HWID=...`\n"
        "- Arceus-X: `https://spdmteam.com/...`"
    )
    embed = discord.Embed(
        title="Supported Links",
        description=supported_links,
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} ({bot.user.id})')
    try:
        await bot.tree.sync()  # Sync commands to the server
        print("Commands synced successfully.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    print(f"An error occurred in event: {event}")

# Run the bot
try:
    bot.run(TOKEN)
except discord.LoginFailure:
    print("Failed to log in: Invalid token")
except Exception as e:
    print(f"An error occurred: {e}")
