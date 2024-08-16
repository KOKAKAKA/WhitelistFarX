import discord
from discord.ext import commands
import os
import json

# Load the bot token from the token.json file
def load_token():
    with open('Commands/Asset/token.json', 'r') as f:
        data = json.load(f)
    return data['token']

# Define bot with command prefix
bot = commands.Bot(command_prefix='/', intents=discord.Intents.default())

# Load the cogs (command modules)
initial_extensions = [
    'Commands.src.Utility.level',
    'Commands.src.RPG.register',
    'Commands.src.RPG.profile',
    'Commands.src.RPG.explore'
]

async def load_extensions():
    for extension in initial_extensions:
        await bot.load_extension(extension)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

    # Load all extensions once the bot is ready
    await load_extensions()

# Start the bot
bot.run(load_token())
