import discord
from discord.ext import commands
from discord import app_commands
import subprocess
from datetime import datetime, timedelta
import json
import aiofiles
import time

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

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(e)
    await update_bot_status()

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

@bot.tree.command(name="whitelist", description="Whitelist a user and generate a key")
@app_commands.describe(user="The user to whitelist", expiration="Expiration time (e.g., 1d, 2h, 1m, 30s, never)", reason="Reason for whitelisting")
async def whitelist(interaction: discord.Interaction, user: discord.User, expiration: str = "never", reason: str = "Not Specified"):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    thinking_message = await interaction.response.send_message("Thinking...", ephemeral=True)

    try:
        url = "http://localhost:18635/generate-key"
        data = run_curl_command(url, method='POST')
        
        if data.get('success'):
            new_key = data['key']
            expiration_str, expiration_date = calculate_expiration(expiration, datetime.utcnow())

            embed = discord.Embed(
                title="Key Service",
                description=f"**User:**\n{user.name} ({user.id})\n**Status:**\nWhitelisted\n**Key:**\n{new_key}\n**Expiration:**\n{expiration_str}\n**Reason:**\n{reason}",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            embed.set_image(url=images["whitelist"])

            try:
                await user.send(embed=embed)
                await update_whitelist_file(user.id, new_key, expiration_str, reason, datetime.utcnow())

                guild = interaction.guild
                member = guild.get_member(user.id)
                if member:
                    role = guild.get_role(WHITELIST_ROLE_ID)
                    if role:
                        await member.add_roles(role)
                
                success_embed = discord.Embed(
                    title="Whitelisting Success",
                    description=f"**User:**\n{user.name} ({user.id})\n**Key:**\n{new_key}\n**Expiration:**\n{expiration_str}\n**Reason:**\n{reason}",
                    color=discord.Color.blue()
                )
                success_embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                success_embed.set_image(url=images["whitelist"])
                await interaction.followup.send(embed=success_embed, ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send(f"Unable to send a DM to {user.name}.", ephemeral=True)
        else:
            await interaction.followup.send('Failed to generate a new key.', ephemeral=True)
    except ValueError as e:
        await interaction.followup.send(f'Error: {e}', ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'Unexpected error: {e}', ephemeral=True)

@bot.tree.command(name="deletekey", description="Delete a key from the server")
@app_commands.describe(key="The key to delete")
async def deletekey(interaction: discord.Interaction, key: str):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    thinking_message = await interaction.response.send_message("Thinking...", ephemeral=True)

    try:
        url = "http://localhost:18635/delete-key"
        data = run_curl_command(url, method='POST', data={"key": key})

        if data.get('success'):
            await update_role_and_key(key, remove_role=True)
            await interaction.followup.send(f"Key '{key}' has been deleted and role removed from whitelisted users.", ephemeral=True)
        else:
            await interaction.followup.send(f"Failed to delete the key '{key}'.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'Error: {e}', ephemeral=True)

@bot.tree.command(name="resethwid", description="Reset HWID for a user")
@app_commands.describe(user="The user to reset HWID for")
async def resethwid(interaction: discord.Interaction, user: discord.User):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    thinking_message = await interaction.response.send_message("Thinking...", ephemeral=True)

    try:
        url = "http://localhost:18635/reset-hwid"
        data = run_curl_command(url, method='POST', data={"user_id": user.id})

        if data.get('success'):
            file_path = 'WhitelistedUser.json'
            async with aiofiles.open(file_path, 'r+') as file:
                users_data = json.loads(await file.read())
                if str(user.id) in users_data:
                    users_data[str(user.id)]['status'] = 'HWID Reset'
                    file.seek(0)
                    await file.write(json.dumps(users_data, indent=4))
                    await file.truncate()

            await interaction.followup.send(f"HWID for user {user.name} has been reset.", ephemeral=True)
        else:
            await interaction.followup.send(f"Failed to reset HWID for user {user.name}.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'Error: {e}', ephemeral=True)

@bot.tree.command(name="profile", description="Get the profile of a whitelisted user")
@app_commands.describe(user="The user to get the profile of")
async def profile(interaction: discord.Interaction, user: discord.User):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user) and interaction.user.id != user.id:
        await interaction.response.send_message("You do not have permission to view this profile.", ephemeral=True)
        return

    # Acknowledge the interaction
    await interaction.response.defer()

    try:
        url = "http://localhost:18635/fetch-keys-hwids"
        response = run_curl_command(url, method='GET')
        response = response.strip()  # Ensure no extraneous whitespace

        # Handle specific response format
        if response.startswith("return "):
            response = response[len("return "):]
        
        # Replace single quotes with double quotes
        response = response.replace("'", '"')

        # Convert response to JSON
        try:
            hwid_data = json.loads(response)
        except json.JSONDecodeError as e:
            await interaction.followup.send(f"Error decoding JSON response: {e}", ephemeral=True)
            return

        key = None
        hwid = 'No HWID found'

        file_path = 'WhitelistedUser.json'
        async with aiofiles.open(file_path, 'r') as file:
            users_data = json.loads(await file.read())
            user_data = users_data.get(str(user.id))

        if user_data:
            key = user_data.get('key')
            if key:
                hwid = hwid_data.get(key, 'No HWID found')

            embed = discord.Embed(
                title="User Profile",
                description=(
                    f"**User:**\n{user.name} ({user.id})\n"
                    f"**Key:**\n{key}\n"
                    f"**HWID:**\n{hwid}\n"
                    f"**Expiration:**\n{user_data.get('expiration', 'Not Specified')}\n"
                    f"**Reason:**\n{user_data.get('reason', 'Not Specified')}\n"
                    f"**Created:**\n{user_data.get('created', 'Not Specified')}\n"
                    f"**Status:**\n{user_data.get('status', 'Not Specified')}"
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            embed.set_image(url=images["profile"])

            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"No data found for user {user.name}.", ephemeral=True)
    except Exception as e:
        error_message = f'Error: {str(e)}'
        if len(error_message) > 2000:
            error_message = error_message[:1997] + '...'  # Truncate to fit within 2000 characters
        await interaction.followup.send(error_message, ephemeral=True)

@bot.tree.command(name="help", description="List all available commands")
async def help_command(interaction: discord.Interaction):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    help_embed = discord.Embed(
        title="Help",
        description=(
            "**/whitelist** - Whitelist a user and generate a key\n"
            "**/deletekey** - Delete a key from the server\n"
            "**/resethwid** - Reset HWID for the whitelisted user\n"
            "**/profile** - View your profile\n"
            "**/help** - Show this help message"
        ),
        color=discord.Color.blue()
    )
    help_embed.set_image(url=images["help"])
    await interaction.response.send_message(embed=help_embed, ephemeral=True)

# Run the bot with the token from the JSON file
bot.run(BOT_TOKEN)
