import discord
from discord.ext import commands
from discord import app_commands
import aiofiles
import aiohttp
import json
import subprocess
from datetime import datetime, timedelta

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
            if role:
                if remove_role:
                    await member.remove_roles(role)
                else:
                    await member.add_roles(role)
                
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

async def run_curl_command_with_retries(url: str, method: str = 'GET', data: dict = None, retries: int = 5, delay: int = 2) -> dict:
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, json=data) as response:
                    response_text = await response.text()
                    if response.status != 200:
                        raise Exception(f'HTTP error: {response.status}')
                    return json.loads(response_text)
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                raise e

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
        await bot.change_presence(status=discord.Status.invisible, activity=None)
    else:
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
        await interaction.response.send_message(embed=discord.Embed(title="Error", description="This command can only be used in the specified server.", color=discord.Color.red()), ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message(embed=discord.Embed(title="Error", description="You do not have permission to use this command.", color=discord.Color.red()), ephemeral=True)
        return

    initial_embed = discord.Embed(title="Thinking", description="Generating key...", color=discord.Color.green())
    await interaction.response.send_message(embed=initial_embed, ephemeral=True)

    try:
        url = "http://localhost:18635/generate-key"
        data = await run_curl_command_with_retries(url, method='POST')

        if data.get('success'):
            new_key = data['key']
            expiration_str, expiration_date = calculate_expiration(expiration, datetime.utcnow())

            success_embed = discord.Embed(
                title="Key Service",
                description = f"""**User:**\n{user.name} ({user.id})\n
                           **Key:**\n<||{new_key}||>\n
                           **Expiration:**\n{expiration_str}\n
                           **Reason:**\n{reason}\n
                           **Status:**\nWhitelisted"""
                color=discord.Color.blue()
            )
            success_embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            success_embed.set_image(url=images["whitelist"])

            try:
                await user.send(embed=success_embed)
                await update_whitelist_file(user.id, new_key, expiration_str, reason, datetime.utcnow())
                await update_role_and_key(user.id)

                confirmation_embed = discord.Embed(
                    title="Whitelisting Success",
                    description = f"""**User:**\n{user.name} ({user.id})\n
                           **Key:**\n<||{new_key}||>\n
                           **Expiration:**\n{expiration_str}\n
                           **Reason:**\n{reason}\n
                           **Status:**\nWhitelisted")"""
                           color=discord.Color.blue()
                )
                confirmation_embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                confirmation_embed.set_image(url=images["whitelist"])
                await interaction.followup.send(embed=confirmation_embed, ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send(embed=discord.Embed(title="Error", description=f"Unable to send a DM to {user.name}.", color=discord.Color.red()), ephemeral=True)
        else:
            await interaction.followup.send(embed=discord.Embed(title="Error", description="Failed to generate a new key.", color=discord.Color.red()), ephemeral=True)
    except ValueError as e:
        await interaction.followup.send(embed=discord.Embed(title="Error", description=f'Error: {e}', color=discord.Color.red()), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Error", description=f'Unexpected error: {e}', color=discord.Color.red()), ephemeral=True)


@bot.tree.command(name="deletekey", description="Delete a key from the server")
@app_commands.describe(key="The key to delete")
async def deletekey(interaction: discord.Interaction, key: str):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message(embed=discord.Embed(title="Error", description="This command can only be used in the specified server.", color=discord.Color.red()), ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message(embed=discord.Embed(title="Error", description="You do not have permission to use this command.", color=discord.Color.red()), ephemeral=True)
        return

    initial_embed = discord.Embed(title="Thinking", description="Deleting key...", color=discord.Color.green())
    await interaction.response.send_message(embed=initial_embed, ephemeral=True)

    try:
        url = "http://localhost:18635/delete-key"
        data = await run_curl_command_with_retries(url, method='POST', data={"key": key})

        if data.get('success'):
            await update_role_and_key(key, remove_role=True)
            success_embed = discord.Embed(
                title="Key Deleted",
                description=f"Key '{key}' has been deleted and role removed from whitelisted users.",
                color=discord.Color.red()
            )
            success_embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            success_embed.set_image(url=images["delete_key"])
            await interaction.followup.send(embed=success_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=discord.Embed(title="Error", description=f"Failed to delete the key '{key}'.", color=discord.Color.red()), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Error", description=f'Error: {e}', color=discord.Color.red()), ephemeral=True)


@bot.tree.command(name="resethwid", description="Reset HWID for a user")
@app_commands.describe(user="The user to reset HWID for")
async def resethwid(interaction: discord.Interaction, user: discord.User):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message(embed=discord.Embed(title="Error", description="This command can only be used in the specified server.", color=discord.Color.red()), ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message(embed=discord.Embed(title="Error", description="You do not have permission to use this command.", color=discord.Color.red()), ephemeral=True)
        return

    initial_embed = discord.Embed(title="Thinking", description="Resetting HWID...", color=discord.Color.green())
    await interaction.response.send_message(embed=initial_embed, ephemeral=True)

    try:
        url = "http://localhost:18635/reset-hwid"
        data = await run_curl_command_with_retries(url, method='POST', data={"user_id": user.id})

        if data.get('success'):
            file_path = 'WhitelistedUser.json'
            async with aiofiles.open(file_path, 'r+') as file:
                users_data = json.loads(await file.read())
                if str(user.id) in users_data:
                    users_data[str(user.id)]['status'] = 'HWID Reset'
                    file.seek(0)
                    await file.write(json.dumps(users_data, indent=4))
                    await file.truncate()

            success_embed = discord.Embed(
                title="HWID Reset",
                description=f"HWID for user {user.name} has been reset.",
                color=discord.Color.orange()
            )
            success_embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            success_embed.set_image(url=images["reset_hwid"])
            await interaction.followup.send(embed=success_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=discord.Embed(title="Error", description=f"Failed to reset HWID for user {user.name}.", color=discord.Color.red()), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Error", description=f'Error: {e}', color=discord.Color.red()), ephemeral=True)

@bot.tree.command(name="help", description="List all available commands")
async def help_command(interaction: discord.Interaction):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message(embed=discord.Embed(title="Error", description="This command can only be used in the specified server.", color=discord.Color.red()), ephemeral=True)
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

@bot.tree.command(name="profile", description="Get the profile of a whitelisted user")
@app_commands.describe(user="The user to get the profile of")
async def profile(interaction: discord.Interaction, user: discord.User = None):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message(embed=discord.Embed(title="Error", description="This command can only be used in the specified server.", color=discord.Color.red()), ephemeral=True)
        return

    if user is None:
        user = interaction.user

    if not is_whitelist_admin(interaction.user) and user != interaction.user:
        await interaction.response.send_message(embed=discord.Embed(title="Error", description="You do not have permission to view this profile.", color=discord.Color.red()), ephemeral=True)
        return

    # Acknowledge the interaction with an ephemeral embed
    initial_embed = discord.Embed(title="Thinking", description="Fetching profile data...", color=discord.Color.green())
    await interaction.response.send_message(embed=initial_embed, ephemeral=True)
    await command_cooldown()  # Add delay for server restart

    try:
        url = "http://localhost:18635/fetch-keys-hwids"
        response = await run_curl_command_with_retries(url, method='GET')
        response = response.strip()

        if response.startswith("return "):
            response = response[len("return "):]
        
        response = response.replace("'", '"')

        try:
            hwid_data = json.loads(response)
        except json.JSONDecodeError as e:
            error_embed = discord.Embed(title="Error", description=f"Error decoding JSON response: {e}", color=discord.Color.red())
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        file_path = 'WhitelistedUser.json'
        async with aiofiles.open(file_path, 'r') as file:
            users_data = json.loads(await file.read())
            user_data = users_data.get(str(user.id))

        if user_data:
            key = user_data.get('key')
            hwid = hwid_data.get(key, 'No HWID found') if key else 'No HWID found'
            created_date = user_data.get('created', 'Not Specified')
            expiration = user_data.get('expiration', 'Not Specified')
            reason = user_data.get('reason', 'Not Specified')
            status = user_data.get('status', 'Not Specified')

            description = (f"**User:**\n{user.name} ({user.id})\n"
                           f"**Key:**\n<||{key}||>\n"
                           f"**HWID:**\n<||{hwid}||>\n"
                           f"**Created:**\n{created_date}\n"
                           f"**Expiration:**\n{expiration}\n"
                           f"**Reason:**\n{reason}\n"
                           f"**Status:**\n{status}")
        else:
            description = f"No data found for user {user.name}."

        profile_embed = discord.Embed(title="User Profile", description=description, color=discord.Color.blue())
        
        # Add image URL at the bottom of the embed
        if "profile" in images:
            profile_embed.set_image(url=images["profile"])
        await interaction.followup.send(embed=profile_embed, ephemeral=True)

    except Exception as e:
        error_message = f'Error: {str(e)}'
        if len(error_message) > 2000:
            error_message = error_message[:1997] + '...'
        error_embed = discord.Embed(title="Error", description=error_message, color=discord.Color.red())
        await interaction.followup.send(embed=error_embed, ephemeral=True)

# Run the bot with the token from the JSON file
bot.run(BOT_TOKEN)
