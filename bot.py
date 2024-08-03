import discord
from discord.ext import commands
from discord import app_commands
import json
import logging
import asyncio
import aiohttp
from datetime import datetime, timedelta
import random

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

# Define a list of images for various actions
images = {
    "help": ["https://cdn.pfps.gg/banners/2466-shooting-star.gif"],
    "whitelist": ["https://cdn.pfps.gg/banners/2919-cat.gif"],
    "delete_key": ["https://cdn.pfps.gg/banners/1948-aesthetic.gif"],
    "reset_hwid": ["https://cdn.pfps.gg/banners/3222-aesthetic-blue.gif"],
    "profile": ["https://cdn.pfps.gg/banners/2919-cat.gif"]
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
                error_text = await response.text()
                logging.error(f'HTTP Error: {response.status} - {error_text}')
                raise Exception(f'HTTP Error: {response.status} - {error_text}')
            try:
                return await response.json()
            except json.JSONDecodeError:
                text = await response.text()
                logging.error(f'Invalid JSON response: {text}')
                raise ValueError(f'Invalid JSON response: {text}')

def create_embed(title: str, description: str, color: discord.Color, image_url: str = None) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    if image_url:
        embed.set_image(url=image_url)
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
        await interaction.followup.send(embed=create_embed("Error", "This command can only be used in the specified server.", discord.Color.red()), ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.followup.send(embed=create_embed("Error", "You do not have permission to use this command.", discord.Color.red()), ephemeral=True)
        return

    try:
        response_data = await run_http_request(url, method, json_data)
        if response_data.get('success'):
            if role_action:
                await role_action()
            await interaction.followup.send(embed=create_embed("Success", success_message, discord.Color.blue(), random.choice(images['help'])), ephemeral=True)
        else:
            await interaction.followup.send(embed=create_embed("Error", failure_message, discord.Color.red(), random.choice(images['help'])), ephemeral=True)
    except discord.errors.HTTPException as e:
        logging.error(f'HTTP Exception: {e}')
        if 'Interaction has already been acknowledged' in str(e):
            await interaction.followup.send(embed=create_embed("Error", "Interaction already acknowledged.", discord.Color.red()), ephemeral=True)
        else:
            await interaction.followup.send(embed=create_embed("Error", f'Error: {e}', discord.Color.red(), random.choice(images['help'])), ephemeral=True)

async def update_whitelist_file(user_id: int, key: str, expiration: str, reason: str, created_at: datetime):
    data = {
        str(user_id): {
            'key': key,
            'expiration': expiration,
            'reason': reason,
            'created': created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'status': 'Active'
        }
    }
    try:
        with open('WhitelistedUser.json', 'r+') as file:
            try:
                users_data = json.load(file)
            except json.JSONDecodeError:
                users_data = {}
            users_data.update(data)
            file.seek(0)
            json.dump(users_data, file, indent=4)
            file.truncate()
    except FileNotFoundError:
        with open('WhitelistedUser.json', 'w') as file:
            json.dump(data, file, indent=4)
    except IOError as e:
        logging.error(f"I/O error occurred: {e}")

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
    try:
        with open('WhitelistedUser.json', 'r+') as file:
            users_data = json.load(file)
            if str(user_id) in users_data:
                del users_data[str(user_id)]
                file.seek(0)
                json.dump(users_data, file, indent=4)
                file.truncate()
    except FileNotFoundError:
        logging.error("WhitelistedUser.json not found.")
    except IOError as e:
        logging.error(f"I/O error occurred: {e}")

async def handle_command_interaction(interaction: discord.Interaction, command_func, *args):
    if not interaction.response.is_done():
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.HTTPException as e:
            logging.error(f'Error deferring interaction: {e}')
            return
    await command_func(interaction, *args)

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
    
    await handle_command_interaction(interaction, whitelist_command_logic, url, 'POST', None, success_message, failure_message, add_role, user, expiration, reason)

async def whitelist_command_logic(interaction, url, method, json_data, success_message, failure_message, role_action, user, expiration, reason):
    expiration_str, expiration_date = calculate_expiration(expiration, datetime.utcnow())
    if expiration_str == 'Invalid format':
        await interaction.followup.send(embed=create_embed("Error", "Invalid expiration format.", discord.Color.red(), random.choice(images['whitelist'])), ephemeral=True)
        return
    await update_whitelist_file(user.id, "some_generated_key", expiration_str, reason, datetime.utcnow())
    await role_action()
    await interaction.followup.send(embed=create_embed("Success", f"Whitelisted {user.name} ({user.id}) with key: some_generated_key\nExpiration: {expiration_str}\nReason: {reason}", discord.Color.blue(), random.choice(images['whitelist'])), ephemeral=True)

@bot.tree.command(name="delete-key", description="Delete a user's key from the whitelist")
@app_commands.describe(user="The user whose key to delete")
async def delete_key(interaction: discord.Interaction, user: discord.User):
    url = "http://localhost:18635/delete-key"
    success_message = f"Deleted the key for {user.name} ({user.id})."
    failure_message = 'Failed to delete the key.'

    async def remove_role():
        guild = interaction.guild
        member = guild.get_member(user.id)
        if member:
            role = guild.get_role(WHITELIST_ROLE_ID)
            if role:
                await member.remove_roles(role)
    
    await handle_command_interaction(interaction, handle_command, url, 'POST', None, success_message, failure_message, remove_role)

@bot.tree.command(name="reset-hwid", description="Reset the HWID for a user")
@app_commands.describe(user="The user whose HWID to reset")
async def reset_hwid(interaction: discord.Interaction, user: discord.User):
    url = "http://localhost:18635/reset-hwid"
    success_message = f"Reset HWID for {user.name} ({user.id})."
    failure_message = 'Failed to reset HWID.'

    await handle_command_interaction(interaction, handle_command, url, 'POST', None, success_message, failure_message)

@bot.tree.command(name="profile", description="Get the profile of a user")
@app_commands.describe(user="The user whose profile to get")
async def profile(interaction: discord.Interaction, user: discord.User):
    url = f"http://localhost:18635/profile?userid={user.id}"
    success_message = f"Profile information for {user.name} ({user.id})."
    failure_message = 'Failed to retrieve profile information.'

    async def send_profile():
        response_data = await run_http_request(url, 'GET')
        description = f"Profile for {user.name} ({user.id}):\n"
        if 'key' in response_data:
            description += f"Key: {response_data['key']}\n"
        if 'hwid' in response_data:
            description += f"HWID: {response_data['hwid']}\n"
        await interaction.followup.send(embed=create_embed("Profile", description, discord.Color.blue(), random.choice(images['profile'])), ephemeral=True)
    
    await handle_command_interaction(interaction, send_profile)

async def main():
    await bot.start(BOT_TOKEN)
    await process_queue()

if __name__ == '__main__':
    asyncio.run(main())
