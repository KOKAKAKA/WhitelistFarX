import discord
from discord.ext import commands
from discord import app_commands
import subprocess
from datetime import datetime, timedelta
import json
import aiofiles
import asyncio
from collections import deque

def load_token():
    with open('SavedToken.json', 'r') as file:
        data = json.load(file)
        return data.get('BOT_TOKEN')

BOT_TOKEN = load_token()

if BOT_TOKEN is None:
    raise ValueError("BOT_TOKEN is not set in SavedToken.json.")

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

ALLOWED_GUILD_ID = 1253670424345051146
WHITELIST_ROLE_ID = 1264472016933621770
WHITELIST_ADMIN_ROLE_ID = 1253779865644175420

images = {
    "help": "https://cdn.pfps.gg/banners/2466-shooting-star.gif",
    "whitelist": "https://cdn.pfps.gg/banners/2919-cat.gif",
    "delete_key": "https://cdn.pfps.gg/banners/1948-aesthetic.gif",
    "reset_hwid": "https://cdn.pfps.gg/banners/3222-aesthetic-blue.gif",
    "profile": "https://cdn.pfps.gg/banners/2919-cat.gif"
}

last_command_time = datetime.utcnow()  # Track the time of the last command
command_queue = deque()  # Queue for commands
queue_lock = asyncio.Lock()  # Lock for queue access

async def update_whitelist_file(user_id: int, key: str, expiration: str, reason: str, created: datetime):
    file_path = 'WhitelistedUser.json'
    data = {
        'key': key,
        'expiration': expiration,
        'reason': reason,
        'created': created.strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'Active'
    }

    try:
        async with aiofiles.open(file_path, 'r+') as file:
            users_data = json.loads(await file.read())
            users_data[str(user_id)] = data
            file.seek(0)
            await file.write(json.dumps(users_data, indent=4))
            await file.truncate()
    except FileNotFoundError:
        async with aiofiles.open(file_path, 'w') as file:
            users_data = {str(user_id): data}
            await file.write(json.dumps(users_data, indent=4))

async def update_role_and_key(user_id: int, remove_role: bool = False):
    guild = discord.utils.get(bot.guilds, id=ALLOWED_GUILD_ID)
    if guild:
        member = guild.get_member(user_id)
        if member:
            role = guild.get_role(WHITELIST_ROLE_ID)
            if role and remove_role:
                await member.remove_roles(role)
                
    file_path = 'WhitelistedUser.json'
    try:
        async with aiofiles.open(file_path, 'r+') as file:
            users_data = json.loads(await file.read())
            if str(user_id) in users_data:
                del users_data[str(user_id)]
                file.seek(0)
                await file.write(json.dumps(users_data, indent=4))
                await file.truncate()
    except FileNotFoundError:
        pass

def is_whitelist_admin(member: discord.Member) -> bool:
    return WHITELIST_ADMIN_ROLE_ID in [role.id for role in member.roles]

def calculate_expiration(expiration: str, now: datetime) -> (str, datetime):
    if expiration.lower() == 'never':
        return 'Never', None
    if expiration.endswith('d'):
        days = int(expiration[:-1])
        expiration_date = now + timedelta(days=days)
    elif expiration.endswith('h'):
        hours = int(expiration[:-1])
        expiration_date = now + timedelta(hours=hours)
    elif expiration.endswith('m'):
        minutes = int(expiration[:-1])
        expiration_date = now + timedelta(minutes=minutes)
    elif expiration.endswith('s'):
        seconds = int(expiration[:-1])
        expiration_date = now + timedelta(seconds=seconds)
    else:
        return 'Invalid format', None
    return expiration_date.strftime('%Y-%m-%d %H:%M:%S UTC'), expiration_date

def run_curl_command(url: str, method: str = 'GET', data: dict = None) -> str:
    command = ['curl', '-X', method, url]

    if data:
        command += ['-d', json.dumps(data), '-H', 'Content-Type: application/json']

    print(f"Running command: {' '.join(command)}")  # Debug: Print command being run

    result = subprocess.run(command, capture_output=True, text=True)

    print(f"Command result: {result.stdout}")  # Debug: Print command result

    if result.returncode != 0:
        raise Exception(f'curl error: {result.stderr}')

    return result.stdout.strip()  # Ensure no extraneous whitespace

async def handle_command_queue():
    while True:
        async with queue_lock:
            if command_queue:
                interaction, command_function = command_queue.popleft()
                try:
                    await command_function()
                except Exception as e:
                    await interaction.response.send_message(f'Unexpected error: {e}', ephemeral=True)
        await asyncio.sleep(1)  # Check queue every second

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(e)
    await update_bot_status()
    bot.loop.create_task(handle_command_queue())

async def update_bot_status():
    global last_command_time
    now = datetime.utcnow()
    elapsed_time = (now - last_command_time).total_seconds()

    if elapsed_time > 30:
        # If more than 30 seconds have passed, set status to invisible and no activity
        await bot.change_presence(status=discord.Status.invisible, activity=None)
    else:
        # Otherwise, set the status to streaming
        await bot.change_presence(
            activity=discord.Streaming(name="Synthia Whitelist Service", url="https://www.twitch.tv/discord")
        )

@bot.event
async def on_command_completion(ctx):
    global last_command_time
    last_command_time = datetime.utcnow()
    await update_bot_status()

# Function to check global cooldown and queue commands if necessary
async def check_global_cooldown(interaction: discord.Interaction):
    global last_command_time
    now = datetime.utcnow()
    elapsed_time = (now - last_command_time).total_seconds()
    if elapsed_time < 10:
        # Add the command to the queue
        async def command_function():
            embed = discord.Embed(
                title="Cooldown",
                description="Please wait before using another command.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await asyncio.sleep(10 - elapsed_time)
            await interaction.response.edit_message(content="Processing your command now...")
            await interaction.response.send_message("Processing your command now...")
        async with queue_lock:
            command_queue.append((interaction, command_function))
        return False  # Skip executing the command
    return True  # Continue with executing the command

async def send_thinking_embed(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Processing...",
        description="Please wait while we handle your request.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def send_error_embed(interaction: discord.Interaction, message: str):
    embed = discord.Embed(
        title="Error",
        description=message,
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def send_success_embed(interaction: discord.Interaction, title: str, description: str):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="whitelist", description="Whitelist a user and generate a key")
@app_commands.describe(user="The user to whitelist", expiration="Expiration time (e.g., 1d, 2h, 1m, 30s, never)", reason="Reason for whitelisting")
async def whitelist(interaction: discord.Interaction, user: discord.User, expiration: str = "never", reason: str = "Not Specified"):
    if not await check_global_cooldown(interaction):
        return

    if interaction.guild.id != ALLOWED_GUILD_ID:
        await send_error_embed(interaction, "This command can only be used in the specified server.")
        return

    if not is_whitelist_admin(interaction.user):
        await send_error_embed(interaction, "You do not have permission to use this command.")
        return

    await send_thinking_embed(interaction)

    try:
        url = "http://localhost:18635/generate-key"
        response = run_curl_command(url, method='POST')
        data = json.loads(response)

        if data.get('status') == 'error':
            await send_error_embed(interaction, data.get('message', 'An error occurred while generating the key.'))
            return

        key = data.get('key')
        now = datetime.utcnow()
        expiration_date_str, expiration_date = calculate_expiration(expiration, now)

        await update_whitelist_file(user.id, key, expiration_date_str, reason, now)
        await send_success_embed(interaction, "Whitelisted Successfully", f"User: {user}\nKey: `{key}`\nExpiration: {expiration_date_str}\nReason: {reason}")

    except Exception as e:
        await send_error_embed(interaction, f'Unexpected error: {e}')

@bot.tree.command(name="deletekey", description="Remove a key from the whitelist")
@app_commands.describe(user="The user whose key you want to remove")
async def delete_key(interaction: discord.Interaction, user: discord.User):
    if not await check_global_cooldown(interaction):
        return

    if interaction.guild.id != ALLOWED_GUILD_ID:
        await send_error_embed(interaction, "This command can only be used in the specified server.")
        return

    if not is_whitelist_admin(interaction.user):
        await send_error_embed(interaction, "You do not have permission to use this command.")
        return

    await send_thinking_embed(interaction)

    try:
        await update_role_and_key(user.id, remove_role=True)
        await send_success_embed(interaction, "Key Removed", f"The whitelist key for {user} has been removed.")

    except Exception as e:
        await send_error_embed(interaction, f'Unexpected error: {e}')

@bot.tree.command(name="reset-hwid", description="Reset HWID for a user")
@app_commands.describe(user="The user whose HWID you want to reset")
async def reset_hwid(interaction: discord.Interaction, user: discord.User):
    if not await check_global_cooldown(interaction):
        return

    if interaction.guild.id != ALLOWED_GUILD_ID:
        await send_error_embed(interaction, "This command can only be used in the specified server.")
        return

    if not is_whitelist_admin(interaction.user):
        await send_error_embed(interaction, "You do not have permission to use this command.")
        return

    await send_thinking_embed(interaction)

    try:
        url = "http://localhost:18635/reset-hwid"
        response = run_curl_command(url, method='POST', data={'user': user.id})
        data = json.loads(response)

        if data.get('status') == 'error':
            await send_error_embed(interaction, data.get('message', 'An error occurred while resetting HWID.'))
            return

        await send_success_embed(interaction, "HWID Reset Successfully", f"The HWID for {user} has been reset.")

    except Exception as e:
        await send_error_embed(interaction, f'Unexpected error: {e}')

@bot.tree.command(name="profile", description="View a user's profile")
@app_commands.describe(user="The user whose profile you want to view")
async def profile(interaction: discord.Interaction, user: discord.User):
    if not await check_global_cooldown(interaction):
        return

    if interaction.guild.id != ALLOWED_GUILD_ID:
        await send_error_embed(interaction, "This command can only be used in the specified server.")
        return

    if not is_whitelist_admin(interaction.user):
        await send_error_embed(interaction, "You do not have permission to use this command.")
        return

    await send_thinking_embed(interaction)

    try:
        url = "http://localhost:18635/fetch-keys-hwids"
        response = run_curl_command(url)
        data = json.loads(response)

        if data.get('status') == 'error':
            await send_error_embed(interaction, data.get('message', 'An error occurred while fetching profile information.'))
            return

        key_info = data.get('keys', {}).get(str(user.id), "No key found")
        hwid_info = data.get('hwids', {}).get(str(user.id), "No HWID found")

        description = f"**Keys:** {key_info}\n**HWID:** {hwid_info}"

        await send_success_embed(interaction, f"{user}'s Profile", description)

    except Exception as e:
        await send_error_embed(interaction, f'Unexpected error: {e}')

@bot.tree.command(name="help", description="Display a list of available commands")
async def help_command(interaction: discord.Interaction):
    if not await check_global_cooldown(interaction):
        return

    embed = discord.Embed(
        title="Help - Available Commands",
        description="Here are the commands you can use:",
        color=discord.Color.blue()
    )

    embed.add_field(name="/whitelist", value="Whitelist a user and generate a key.", inline=False)
    embed.add_field(name="/deletekey", value="Remove a key from the whitelist.", inline=False)
    embed.add_field(name="/reset-hwid", value="Reset HWID for a user.", inline=False)
    embed.add_field(name="/profile", value="View a user's profile.", inline=False)
    embed.set_footer(text="For more information, use the command you need.")

    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(BOT_TOKEN)
