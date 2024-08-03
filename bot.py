import discord
from discord.ext import commands
from discord import app_commands
import json
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load bot token from SavedToken.json
def load_token():
    try:
        with open('SavedToken.json', 'r') as file:
            data = json.load(file)
            return data.get('BOT_TOKEN')
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Failed to load token: {e}")
        return None

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

# Global cooldown and queue
command_queue = asyncio.Queue()
global_cooldown = 2.0  # 2 seconds

def is_whitelist_admin(member: discord.Member) -> bool:
    return WHITELIST_ADMIN_ROLE_ID in [role.id for role in member.roles]

def calculate_expiration(expiration: str, now: datetime) -> (str, datetime):
    try:
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
            raise ValueError("Invalid expiration format.")
        return expiration_date.strftime('%Y-%m-%d %H:%M:%S UTC'), expiration_date
    except Exception as e:
        logging.error(f'Error calculating expiration: {e}')
        return 'Invalid format', None

async def run_http_request(url: str, method: str = 'GET', json_data: dict = None) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, json=json_data) as response:
            logging.info(f'HTTP Request to {url} - Status: {response.status}')
            if response.status != 200:
                raise Exception(f'HTTP Error: {response.status} - {await response.text()}')

            try:
                return await response.json()
            except json.JSONDecodeError:
                raise ValueError(f'Invalid JSON response: {await response.text()}')

def create_embed(title: str, description: str, color: discord.Color) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    return embed

async def process_queue():
    while True:
        command, interaction, url, method, json_data, success_message, failure_message, role_action = await command_queue.get()
        try:
            await handle_command(interaction, url, method, json_data, success_message, failure_message, role_action)
        except Exception as e:
            logging.error(f'Error processing command: {e}')
        finally:
            command_queue.task_done()
            await asyncio.sleep(global_cooldown)

async def handle_command(interaction: discord.Interaction, url: str, method: str, json_data: dict = None, success_message: str = '', failure_message: str = '', role_action: callable = None):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message(embed=create_embed("Error", "This command can only be used in the specified server.", discord.Color.red()), ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message(embed=create_embed("Error", "You do not have permission to use this command.", discord.Color.red()), ephemeral=True)
        return

    thinking_message = await interaction.response.send_message(embed=create_embed("Thinking", "Processing your request...", discord.Color.green()), ephemeral=True)

    try:
        response_data = await run_http_request(url, method, json_data)
        if response_data.get('success'):
            if role_action:
                await role_action()
            await interaction.followup.send(embed=create_embed("Success", success_message, discord.Color.blue()), ephemeral=True)
        else:
            await interaction.followup.send(embed=create_embed("Error", failure_message, discord.Color.red()), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=create_embed("Error", f'Error: {e}', discord.Color.red()), ephemeral=True)

async def update_whitelist_file(user_id: int, key: str, expiration: str, reason: str, created_at: datetime):
    try:
        with open('WhitelistedUser.json', 'r+') as file:
            try:
                users_data = json.load(file)
            except json.JSONDecodeError:
                users_data = {}
            
            users_data[str(user_id)] = {
                'key': key,
                'expiration': expiration,
                'reason': reason,
                'created': created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'status': 'Active'
            }
            file.seek(0)
            json.dump(users_data, file, indent=4)
            file.truncate()
    except FileNotFoundError:
        with open('WhitelistedUser.json', 'w') as file:
            users_data = {
                str(user_id): {
                    'key': key,
                    'expiration': expiration,
                    'reason': reason,
                    'created': created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'status': 'Active'
                }
            }
            json.dump(users_data, file, indent=4)

async def update_role_and_key(user_id: int, remove_role: bool = False):
    guild = discord.utils.get(bot.guilds, id=ALLOWED_GUILD_ID)
    if guild:
        member = guild.get_member(user_id)
        if member:
            role = guild.get_role(WHITELIST_ROLE_ID)
            if role and remove_role:
                await member.remove_roles(role)
                
    with open('WhitelistedUser.json', 'r+') as file:
        users_data = json.load(file)
        if str(user_id) in users_data:
            del users_data[str(user_id)]
            file.seek(0)
            json.dump(users_data, file, indent=4)
            file.truncate()

@bot.tree.command(name="whitelist", description="Whitelist a user and generate a key")
@app_commands.describe(user="The user to whitelist", expiration="Expiration time (e.g., 1d, 2h, 1m, 30s, never)", reason="Reason for whitelisting")
async def whitelist(interaction: discord.Interaction, user: discord.User, expiration: str = "never", reason: str = "Not Specified"):
    url = "http://localhost:18635/generate-key"
    success_message = f"Whitelisted {user.name} ({user.id}) with a key."
    failure_message = 'Failed to generate a new key.'

    async def add_role():
        guild = interaction.guild
        member = guild.get_member(user.id)
        if member:
            role = guild.get_role(WHITELIST_ROLE_ID)
            if role:
                await member.add_roles(role)
    
    try:
        response_data = await run_http_request(url, method='POST')
        if response_data.get('success'):
            new_key = response_data['key']
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
                await command_queue.put((whitelist, interaction, url, 'POST', {'key': new_key}, success_message, failure_message, add_role))
            except discord.Forbidden:
                await interaction.followup.send(embed=create_embed("Error", f"Unable to send a DM to {user.name}.", discord.Color.red()), ephemeral=True)
        else:
            await interaction.followup.send(embed=create_embed("Error", failure_message, discord.Color.red()), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=create_embed("Error", f'Unexpected error: {e}', discord.Color.red()), ephemeral=True)

@bot.tree.command(name="deletekey", description="Delete a key from the server")
@app_commands.describe(key="The key to delete")
async def delete_key(interaction: discord.Interaction, key: str):
    url = "http://localhost:18635/delete-key"
    success_message = f"Key '{key}' has been deleted and role removed from whitelisted users."
    failure_message = f"Failed to delete the key '{key}'."

    async def remove_roles():
        with open('WhitelistedUser.json', 'r+') as file:
            users_data = json.load(file)
            users_to_remove = [user_id for user_id, info in users_data.items() if info['key'] == key]
            for user_id in users_to_remove:
                del users_data[user_id]
                guild = discord.utils.get(bot.guilds, id=ALLOWED_GUILD_ID)
                if guild:
                    member = guild.get_member(int(user_id))
                    if member:
                        role = guild.get_role(WHITELIST_ROLE_ID)
                        if role:
                            await member.remove_roles(role)
            file.seek(0)
            json.dump(users_data, file, indent=4)
            file.truncate()

    await command_queue.put((delete_key, interaction, url, 'POST', {'key': key}, success_message, failure_message, remove_roles))

@bot.tree.command(name="resethwid", description="Reset HWID for a user")
@app_commands.describe(user="The user to reset HWID for")
async def resethwid(interaction: discord.Interaction, user: discord.User):
    url = "http://localhost:18635/reset-hwid"
    success_message = f"HWID for user {user.name} has been reset."
    failure_message = f"Failed to reset HWID for user {user.name}."

    async def update_status():
        with open('WhitelistedUser.json', 'r+') as file:
            users_data = json.load(file)
            if str(user.id) in users_data:
                users_data[str(user.id)]['status'] = 'HWID Reset'
                file.seek(0)
                json.dump(users_data, file, indent=4)
                file.truncate()

    await command_queue.put((resethwid, interaction, url, 'POST', {'user_id': user.id}, success_message, failure_message, update_status))

@bot.tree.command(name="profile", description="Get the profile of a whitelisted user")
@app_commands.describe(user="The user to get the profile of")
async def profile(interaction: discord.Interaction, user: discord.User):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message(embed=create_embed("Error", "This command can only be used in the specified server.", discord.Color.red()), ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user) and interaction.user.id != user.id:
        await interaction.response.send_message(embed=create_embed("Error", "You do not have permission to view this profile.", discord.Color.red()), ephemeral=True)
        return

    thinking_message = await interaction.response.send_message(embed=create_embed("Thinking", "Processing your request...", discord.Color.green()), ephemeral=True)

    try:
        with open('WhitelistedUser.json', 'r') as file:
            users_data = json.load(file)
            user_data = users_data.get(str(user.id))

        if user_data:
            url = f"http://localhost:18635/profile?userid={user.id}"
            response_data = await run_http_request(url, method='GET')

            hwid_info = response_data.get('hwid') or 'No HWID associated'

            embed = discord.Embed(
                title="User Profile",
                description=f"**User:**\n{user.name} ({user.id})\n**Key:**\n{user_data['key']}\n**Expiration:**\n{user_data['expiration']}\n**Reason:**\n{user_data['reason']}\n**Created:**\n{user_data['created']}\n**Status:**\n{user_data['status']}\n**HWID:**\n{hwid_info}",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            embed.set_image(url=images["profile"])

            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=create_embed("Error", f"No data found for user {user.name}.", discord.Color.red()), ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=create_embed("Error", f'Error: {e}', discord.Color.red()), ephemeral=True)

@bot.tree.command(name="help", description="List all available commands")
async def help_command(interaction: discord.Interaction):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message(embed=create_embed("Error", "This command can only be used in the specified server.", discord.Color.red()), ephemeral=True)
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

@bot.event
async def on_ready():
    logging.info(f'Bot is ready. Logged in as {bot.user.name}')
    bot.loop.create_task(process_queue())

# Use async main to start the bot
async def main():
    await bot.start(BOT_TOKEN)

asyncio.run(main())
