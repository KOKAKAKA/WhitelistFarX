import discord
from discord.ext import commands
from discord import app_commands, ButtonStyle, Interaction
from discord.ui import Button, View
import subprocess
from datetime import datetime, timedelta
import json
import os
import time

# Load bot token from SavedToken.json
def load_token():
    file_path = 'SavedToken.json'
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} not found.")
    with open(file_path, 'r') as file:
        data = json.load(file)
        return data.get('BOT_TOKEN')

BOT_TOKEN = load_token()

# Check if the token is loaded
if BOT_TOKEN is None:
    raise ValueError("BOT_TOKEN is not set in SavedToken.json.")

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# The ID of the server where the bot is allowed to operate
ALLOWED_GUILD_ID = 1253670424345051146

# Role IDs
WHITELIST_ROLE_ID = 1264472016933621770
WHITELIST_ADMIN_ROLE_ID = 1253779865644175420

# Image URLs
images = {
    "help": "https://cdn.pfps.gg/banners/2466-shooting-star.gif",
    "whitelist": "https://cdn.pfps.gg/banners/2919-cat.gif",
    "delete_key": "https://cdn.pfps.gg/banners/1948-aesthetic.gif",
    "reset_hwid": "https://cdn.pfps.gg/banners/3222-aesthetic-blue.gif",
    "profile": "https://cdn.pfps.gg/banners/2919-cat.gif"
}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'Error syncing commands: {e}')

def is_whitelist_admin(member: discord.Member) -> bool:
    return WHITELIST_ADMIN_ROLE_ID in [role.id for role in member.roles]

def calculate_expiration(expiration: str, now: datetime) -> (str, datetime):
    if expiration.lower() == 'never':
        return 'Never', None

    try:
        duration, unit = int(expiration[:-1]), expiration[-1]
    except ValueError:
        return 'Invalid format', None

    if unit == 'd':
        expiration_date = now + timedelta(days=duration)
    elif unit == 'h':
        expiration_date = now + timedelta(hours=duration)
    elif unit == 'm':
        expiration_date = now + timedelta(minutes=duration)
    elif unit == 's':
        expiration_date = now + timedelta(seconds=duration)
    else:
        return 'Invalid format', None

    return expiration_date.strftime('%Y-%m-%d %H:%M:%S UTC'), expiration_date

def run_curl_command(url: str, method: str = 'GET', data: dict = None) -> dict:
    command = ['curl', '-X', method, url]
    if data:
        command += ['-d', json.dumps(data), '-H', 'Content-Type: application/json']

    retries = 5
    for attempt in range(retries):
        try:
            print(f'Running command: {" ".join(command)}')
            result = subprocess.run(command, capture_output=True, text=True, timeout=5)
            print(f'Command output: {result.stdout}')
            print(f'Command error: {result.stderr}')

            if result.returncode != 0:
                raise Exception(f'curl error: {result.stderr}')

            response = result.stdout.strip()
            if response.startswith("return "):
                response = response[7:]

            corrected_output = response.replace("'", "\"")
            return json.loads(corrected_output)
        
        except subprocess.TimeoutExpired:
            print(f"Attempt {attempt + 1} of {retries} timed out. Retrying...")
            time.sleep(1)
        except json.JSONDecodeError:
            print(f'JSON decoding failed for response: {corrected_output}')

    raise Exception("Max retries reached. Failed to complete the curl command.")

async def update_role_and_key(user_id: int, remove_role: bool = False):
    guild = discord.utils.get(bot.guilds, id=ALLOWED_GUILD_ID)
    if guild:
        member = guild.get_member(user_id)
        if member:
            role = guild.get_role(WHITELIST_ROLE_ID)
            if role:
                try:
                    if remove_role:
                        print(f"Removing role {role.id} from member {user_id}.")
                        await member.remove_roles(role)
                    else:
                        print(f"Adding role {role.id} to member {user_id}.")
                        await member.add_roles(role)
                except discord.Forbidden:
                    print(f"Insufficient permissions to modify roles for member {user_id}.")
                except discord.HTTPException as e:
                    print(f"HTTP exception occurred while modifying roles: {e}")

    file_path = 'WhitelistedUser.json'
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r+') as file:
                users_data = json.load(file)
                print(f"Users data before removal: {users_data}")
                if str(user_id) in users_data:
                    if not remove_role:
                        print(f"Removing user {user_id} from whitelist.")
                        del users_data[str(user_id)]
                        file.seek(0)
                        json.dump(users_data, file, indent=4)
                        file.truncate()
                        print(f"Updated whitelist file after removal: {users_data}")
        except (IOError, json.JSONDecodeError) as e:
            print(f'Error handling WhitelistedUser.json: {e}')

def update_whitelist_file(user_id: int, key: str, expiration: str, reason: str, request_time: datetime):
    file_path = 'WhitelistedUser.json'
    users_data = {}

    # Ensure the file exists
    if not os.path.exists(file_path):
        with open(file_path, 'w') as file:
            json.dump(users_data, file, indent=4)
    else:
        try:
            with open(file_path, 'r') as file:
                users_data = json.load(file)
        except (IOError, json.JSONDecodeError) as e:
            print(f'Error loading WhitelistedUser.json: {e}')
            users_data = {}

    print(f"Current users_data before update: {users_data}")

    users_data[str(user_id)] = {
        'key': key,
        'expiration': expiration,
        'reason': reason,
        'created': request_time.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'status': 'Whitelisted'
    }

    try:
        # Write changes to the file
        with open(file_path, 'w') as file:
            json.dump(users_data, file, indent=4)
        print(f"Updated users_data: {users_data}")
    except IOError as e:
        print(f'Error writing WhitelistedUser.json: {e}')

def is_key_valid(key):
    try:
        hwid_data = run_curl_command("http://localhost:18635/fetch-keys-hwids")
        return key in hwid_data
    except Exception as e:
        print(f"Error checking key validity: {e}")
        return False

@bot.tree.command(name="whitelist", description="Whitelist a user and generate a key")
@app_commands.describe(user="The user to whitelist", expiration="Expiration time (e.g., 1d, 2h, 1m, 30s, never)", reason="Reason for whitelisting")
async def whitelist(interaction: discord.Interaction, user: discord.User, expiration: str = "never", reason: str = "Not Specified"):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("Thinking...", ephemeral=True)

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
                print(f"Updating whitelist file for user {user.id} with key {new_key}")
                update_whitelist_file(user.id, new_key, expiration_str, reason, datetime.utcnow())
                
                # Verify the file contents after update
                with open('WhitelistedUser.json', 'r') as file:
                    updated_data = json.load(file)
                    print(f"WhitelistedUser.json contents: {updated_data}")

                await update_role_and_key(user.id)
                
                success_embed = discord.Embed(
                    title="Whitelisting Success",
                    description=f"**User:**\n{user.name} ({user.id})\n**Key:**\n{new_key}\n**Expiration:**\n{expiration_str}\n**Reason:**\n{reason}",
                    color=discord.Color.green()
                )
                success_embed.set_image(url=images["whitelist"])
                await interaction.followup.send(embed=success_embed, ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("Unable to send DM to the user.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"Error occurred while whitelisting user: {e}", ephemeral=True)
                print(f"Error sending message or updating role: {e}")
        else:
            await interaction.followup.send("Failed to generate a key.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Error occurred while processing whitelist: {e}", ephemeral=True)
        print(f"Error generating key or running curl command: {e}")

# Add more commands and functionality as needed

bot.run(BOT_TOKEN)
