import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import json
import os
import time
import logging
from filelock import SoftFileLock  # Import SoftFileLock
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    logging.info(f'Logged in as {bot.user.name} ({bot.user.id})')
    try:
        synced = await bot.tree.sync()
        logging.info(f'Synced {len(synced)} command(s)')
    except Exception as e:
        logging.error(f'Error syncing commands: {e}')

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
            logging.info(f'Running command: {" ".join(command)}')
            result = subprocess.run(command, capture_output=True, text=True, timeout=5)
            logging.info(f'Command output: {result.stdout}')
            logging.error(f'Command error: {result.stderr}')

            if result.returncode != 0:
                raise Exception(f'curl error: {result.stderr}')

            response = result.stdout.strip()
            if response.startswith("return "):
                response = response[7:]

            corrected_output = response.replace("'", "\"")
            return json.loads(corrected_output)
        
        except subprocess.TimeoutExpired:
            logging.warning(f"Attempt {attempt + 1} of {retries} timed out. Retrying...")
            time.sleep(1)
        except json.JSONDecodeError:
            logging.error(f'JSON decoding failed for response: {corrected_output}')

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
                        await member.remove_roles(role)
                    else:
                        await member.add_roles(role)
                    logging.info(f"Role {'removed from' if remove_role else 'added to'} user {user_id}.")
                except discord.Forbidden:
                    logging.error(f"Insufficient permissions to modify roles for member {user_id}.")
                except discord.HTTPException as e:
                    logging.error(f"HTTP exception occurred while modifying roles: {e}")

    file_path = 'WhitelistedUser.json'
    lock_path = file_path + '.lock'
    lock = SoftFileLock(lock_path)
    with lock:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r+') as file:
                    users_data = json.load(file)
                    if str(user_id) in users_data:
                        del users_data[str(user_id)]
                        file.seek(0)
                        json.dump(users_data, file, indent=4)
                        file.truncate()
                        logging.info(f"Removed user {user_id} from whitelist.")
            except (IOError, json.JSONDecodeError) as e:
                logging.error(f'Error handling WhitelistedUser.json: {e}')

def update_whitelist_file(user_id, key, expiration, reason, created):
    file_path = 'WhitelistedUser.json'
    lock_path = file_path + '.lock'
    lock = SoftFileLock(lock_path)
    with lock:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as file:
                    users_data = json.load(file)
            else:
                users_data = {}
            
            users_data[user_id] = {
                'key': key,
                'expiration': expiration,
                'reason': reason,
                'created': created,
                'status': 'Whitelisted'
            }
            
            with open(file_path, 'w') as file:
                json.dump(users_data, file, indent=4)
        
        except FileNotFoundError as e:
            logging.error(f'File not found: {e}')
            raise
        except IOError as e:
            logging.error(f'I/O error occurred: {e}')
            raise
        except Exception as e:
            logging.error(f'Unexpected error: {e}')
            raise

def is_key_valid(key):
    try:
        hwid_data = run_curl_command("http://localhost:18635/fetch-keys-hwids")
        return key in hwid_data
    except Exception as e:
        logging.error(f"Error checking key validity: {e}")
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
                logging.info(f"Updating whitelist file for user {user.id}")
                created = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                update_whitelist_file(str(user.id), new_key, expiration_str, reason, created)
                await update_role_and_key(user.id)
                await interaction.followup.send(embed=embed, ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("I can't send a message to the user. They might have DMs disabled.", ephemeral=True)
            except Exception as e:
                logging.error(f'Error sending DM or updating whitelist: {e}')
                await interaction.followup.send("An error occurred while processing the whitelisting request.", ephemeral=True)
        else:
            logging.error("Key generation failed.")
            await interaction.followup.send("Failed to generate a key.", ephemeral=True)
    except Exception as e:
        logging.error(f"An error occurred while processing the whitelisting request: {e}")
        await interaction.followup.send("An error occurred while processing the whitelisting request.", ephemeral=True)

bot.run(BOT_TOKEN)
