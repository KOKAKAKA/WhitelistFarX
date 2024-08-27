import discord
from discord.ext import commands
from discord.ui import Button, View
import aiohttp
import asyncio
import io
import json
import os

# Load token from SavedToken.json
with open('SavedToken.json') as f:
    data = json.load(f)
TOKEN = data['token']

OBFUSCATE_URL = 'http://localhost:8080/obfuscate'
PASTE_BASE_URL = 'http://localhost:8080/paste'

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

preset_selected = None
version_selected = None
method_selected = None

class ObfuscatePanel(View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label='Minify', style=discord.ButtonStyle.primary)
    async def minify_button(self, interaction: discord.Interaction, button: Button):
        global preset_selected
        preset_selected = 'Minify'
        await interaction.response.edit_message(content="Select Lua Version", view=VersionPanel())

    @discord.ui.button(label='Weak', style=discord.ButtonStyle.primary)
    async def weak_button(self, interaction: discord.Interaction, button: Button):
        global preset_selected
        preset_selected = 'Weak'
        await interaction.response.edit_message(content="Select Lua Version", view=VersionPanel())

    @discord.ui.button(label='Medium', style=discord.ButtonStyle.primary)
    async def medium_button(self, interaction: discord.Interaction, button: Button):
        global preset_selected
        preset_selected = 'Medium'
        await interaction.response.edit_message(content="Select Lua Version", view=VersionPanel())

    @discord.ui.button(label='Strong', style=discord.ButtonStyle.primary)
    async def strong_button(self, interaction: discord.Interaction, button: Button):
        global preset_selected
        preset_selected = 'Strong'
        await interaction.response.edit_message(content="Select Lua Version", view=VersionPanel())

class VersionPanel(View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label='Lua51', style=discord.ButtonStyle.secondary)
    async def lua51_button(self, interaction: discord.Interaction, button: Button):
        global version_selected
        version_selected = 'Lua51'
        await interaction.response.edit_message(content="Select Output Method", view=MethodPanel())

    @discord.ui.button(label='LuaU', style=discord.ButtonStyle.secondary)
    async def luau_button(self, interaction: discord.Interaction, button: Button):
        global version_selected
        version_selected = 'LuaU'
        await interaction.response.edit_message(content="Select Output Method", view=MethodPanel())

    @discord.ui.button(label='Default (Newest)', style=discord.ButtonStyle.secondary)
    async def default_button(self, interaction: discord.Interaction, button: Button):
        global version_selected
        version_selected = ''
        await interaction.response.edit_message(content="Select Output Method", view=MethodPanel())

class MethodPanel(View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label='Raw (broken)', style=discord.ButtonStyle.success)
    async def raw_button(self, interaction: discord.Interaction, button: Button):
        global method_selected
        method_selected = 'raw'
        await interaction.response.edit_message(content="Click Obfuscate and attach a file", view=ObfuscateButton())

    @discord.ui.button(label='Download', style=discord.ButtonStyle.success)
    async def download_button(self, interaction: discord.Interaction, button: Button):
        global method_selected
        method_selected = 'download'
        await interaction.response.edit_message(content="Click Obfuscate and attach a file", view=ObfuscateButton())

class ObfuscateButton(View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label='Obfuscate!', style=discord.ButtonStyle.danger)
    async def obfuscate_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Please attach a .lua or .txt file to obfuscate.", ephemeral=True)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Obfuscating Lua Scripts"))
    print(f'Logged in as {bot.user.name}')

@bot.command()
async def panel(ctx):
    embed = discord.Embed(title="Obfuscation Panel", description="Select the obfuscation preset", color=discord.Color.blue())
    await ctx.send(embed=embed, view=ObfuscatePanel())

@bot.event
async def on_message(message):
    global preset_selected, version_selected, method_selected

    # Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    # Check for attachments
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(('.lua', '.txt')):
                # Download and read the file
                content = await attachment.read()
                text_content = content.decode('utf-8')

                if preset_selected and version_selected is not None and method_selected:
                    # Send the Lua code to the /obfuscate endpoint
                    async with aiohttp.ClientSession() as session:
                        async with session.post(OBFUSCATE_URL, json={'code': text_content, 'preset': preset_selected, 'version': version_selected}) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                paste_id = data.get('paste_id')
                                if paste_id:
                                    if method_selected == 'raw':
                                        paste_url = f'https://obfuscated-synthia.serveo.net/paste/{paste_id}/raw'
                                        await message.channel.send(f'Your obfuscated code is available at: {paste_url}')
                                    elif method_selected == 'download':
                                        paste_url = f'https://obfuscated-synthia.serveo.net/download/{paste_id}'
                                        async with session.get(paste_url) as paste_resp:
                                            if paste_resp.status == 200:
                                                file = discord.File(fp=io.BytesIO(await paste_resp.read()), filename=f'{paste_id}.lua')
                                                await message.channel.send(file=file)
                                            else:
                                                await message.channel.send('Error: Failed to retrieve the paste for download.')
                                else:
                                    await message.channel.send('Error: No paste ID returned.')
                            else:
                                error_message = await resp.json()
                                await message.channel.send(f'Error: {error_message.get("error", "Failed to obfuscate the code.")}\nDetails: {error_message.get("details", "")}')

    # Process commands
    await bot.process_commands(message)
@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

bot.run(TOKEN)
