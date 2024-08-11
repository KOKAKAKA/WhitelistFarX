import discord
import json
import requests
from discord.ext import commands

# Load the token from SavedToken.json
with open('SavedToken.json') as token_file:
    token_data = json.load(token_file)
    TOKEN = token_data['token']

# Create a bot instance
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

class BypassModal(discord.ui.Modal, title="Bypass URL"):
    url = discord.ui.TextInput(label="Enter the shortened URL", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            url = str(self.url)

            # Determine which API to call based on the URL pattern
            if "flux.li" in url:
                api_url = f'https://stickx.top/api-fluxus/?hwid={url}&api_key=E99l9NOctud3vmu6bPne'
            elif "gateway.platoboost" in url:
                api_url = f'https://stickx.top/api-delta/?hwid={url}&api_key=E99l9NOctud3vmu6bPne'
            elif "hydrogen" in url:
                api_url = f'https://stickx.top/api-hydrogen/?hwid={url}&api_key=E99l9NOctud3vmu6bPne'
            elif "linkvertise" in url or "link." in url:
                api_url = f'https://stickx.top/api-linkvertise/?link={url}&api_key=E99l9NOctud3vmu6bPne'
            else:
                raise ValueError("Invalid or unsupported URL")

            response = requests.get(api_url)
            data = response.json()

            if data['Status'] == 'Success':
                unshortened_link = data.get('key', 'Link not found')
                embed = discord.Embed(title="Bypass Successful", description=f"[Unshortened link]({unshortened_link})", color=discord.Color.green())
            else:
                embed = discord.Embed(title="Error", description="API call failed", color=discord.Color.red())

        except Exception as e:
            embed = discord.Embed(title="Error", description=f"An error occurred: {str(e)}", color=discord.Color.red())

        await interaction.followup.send(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.tree.command(name="bypass", description="Bypass shortened URLs or executors")
async def bypass(interaction: discord.Interaction):
    await interaction.response.send_modal(BypassModal())

# Run the bot
bot.run(TOKEN)
