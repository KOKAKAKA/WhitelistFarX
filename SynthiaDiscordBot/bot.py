import discord
from discord.ext import commands
from discord import app_commands, ButtonStyle, Interaction
from discord.ui import Button, View
import subprocess
from datetime import datetime, timedelta
import json
import os
import time
import logging

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
                        await member.remove_roles(role)
                    else:
                        await member.add_roles(role)
                    print(f"Role {'removed from' if remove_role else 'added to'} user {user_id}.")
                except discord.Forbidden:
                    print(f"Insufficient permissions to modify roles for member {user_id}.")
                except discord.HTTPException as e:
                    print(f"HTTP exception occurred while modifying roles: {e}")

    file_path = 'WhitelistedUser.json'
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r+') as file:
                users_data = json.load(file)
                if str(user_id) in users_data:
                    del users_data[str(user_id)]
                    file.seek(0)
                    json.dump(users_data, file, indent=4)
                    file.truncate()
                    print(f"Removed user {user_id} from whitelist.")
        except (IOError, json.JSONDecodeError) as e:
            print(f'Error handling WhitelistedUser.json: {e}')

def update_whitelist_file(user_id, key, expiration, reason, created):
    try:
        # Load existing data
        if os.path.exists('WhitelistedUser.json'):
            with open('WhitelistedUser.json', 'r') as file:
                users_data = json.load(file)
        else:
            users_data = {}
        
        # Update data
        users_data[user_id] = {
            'key': key,
            'expiration': expiration,
            'reason': reason,
            'created': created,
            'status': 'Whitelisted'
        }
        
        # Write updated data
        with open('WhitelistedUser.json', 'w') as file:
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
                print(f"Updating whitelist file for user {user.id}")
                created = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                update_whitelist_file(str(user.id), new_key, expiration_str, reason, created)
                await update_role_and_key(user.id)
                await interaction.followup.send(embed=embed, ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send("I can't send a message to the user. They might have DMs disabled.", ephemeral=True)
            except Exception as e:
                print(f"Error sending DM or updating whitelist: {e}")
                await interaction.followup.send("There was an error processing your request.", ephemeral=True)
        else:
            await interaction.followup.send("Failed to generate key.", ephemeral=True)
    except Exception as e:
        print(f"Unexpected error: {e}")
        await interaction.followup.send("There was an error processing your request.", ephemeral=True)

bot.run(BOT_TOKEN)

@bot.tree.command(name="profile", description="Get the profile of a whitelisted user")
@app_commands.describe(user="The user to get the profile of (admin only)")
async def profile(interaction: discord.Interaction, user: discord.User = None):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    if user is None:
        user = interaction.user

    if not is_whitelist_admin(interaction.user) and interaction.user.id != user.id:
        await interaction.response.send_message("You do not have permission to view this profile.", ephemeral=True)
        return

    await interaction.response.defer()  # Use defer to indicate that you are processing

    try:
        file_path = 'WhitelistedUser.json'
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as file:
                    users_data = json.load(file)
                
                # Clean up any stale entries
                valid_users = {}
                for uid, data in users_data.items():
                    if is_key_valid(data['key']):
                        valid_users[uid] = data
                    else:
                        # Update status to "Key Deleted" if key is invalid
                        data['status'] = 'Key Deleted'
                        valid_users[uid] = data

                # Save updated data with "Key Deleted" status
                with open(file_path, 'w') as file:
                    json.dump(valid_users, file, indent=4)

                user_data = valid_users.get(str(user.id))

                if user_data:
                    hwid_data = run_curl_command("http://localhost:18635/fetch-keys-hwids")
                    hwid = hwid_data.get(user_data['key'], "Not Available")

                    embed = discord.Embed(
                        title="User Profile",
                        description=f"**User:**\n{user.name} ({user.id})\n**Key:**\n{user_data['key']}\n**Expiration:**\n{user_data['expiration']}\n**Reason:**\n{user_data['reason']}\n**Created:**\n{user_data['created']}\n**Status:**\n{user_data['status']}\n**HWID:**\n{hwid}",
                        color=discord.Color.blue()
                    )
                    embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                    embed.set_image(url=images["profile"])

                    class ProfileButtons(View):
                        @discord.ui.button(label="Reset HWID", style=ButtonStyle.green)
                        async def reset_hwid_button(self, interaction: Interaction, button: Button):
                            if interaction.user.id != user.id and not is_whitelist_admin(interaction.user):
                                await interaction.response.send_message("You do not have permission to reset HWID for this user.", ephemeral=True)
                                return
                            await self.reset_hwid(interaction, user)

                        async def reset_hwid(self, interaction: Interaction, user: discord.User):
                            url = "http://localhost:18635/reset-hwid"
                            try:
                                file_path = 'WhitelistedUser.json'
                                if os.path.exists(file_path):
                                    try:
                                        with open(file_path, 'r') as file:
                                            users_data = json.load(file)
                                            user_key = users_data.get(str(user.id), {}).get('key')

                                        if user_key:
                                            data = run_curl_command(url, method='POST', data={"key": user_key})

                                            if data.get('success'):
                                                update_whitelist_file(user.id, user_key, users_data[str(user.id)]['expiration'], users_data[str(user.id)]['reason'], datetime.utcnow())

                                                await interaction.response.send_message(f"HWID for user {user.name} has been reset.", ephemeral=True)
                                            else:
                                                await interaction.response.send_message(f"Failed to reset HWID for user {user.name}.", ephemeral=True)
                                        else:
                                            await interaction.response.send_message(f"No key found for user {user.name}.", ephemeral=True)
                                    except (IOError, json.JSONDecodeError) as e:
                                        await interaction.response.send_message(f'Error handling WhitelistedUser.json: {e}', ephemeral=True)
                            except Exception as e:
                                await interaction.response.send_message(f'Error: {e}', ephemeral=True)

                        @discord.ui.button(label="Delete Key", style=ButtonStyle.red)
                        async def delete_key_button(self, interaction: Interaction, button: Button):
                            if interaction.user.id != user.id and not is_whitelist_admin(interaction.user):
                                await interaction.response.send_message("You do not have permission to delete this key.", ephemeral=True)
                                return
                            await self.delete_key(interaction, user)

                        async def delete_key(self, interaction: Interaction, user: discord.User):
                            url = "http://localhost:18635/delete-key"
                            try:
                                file_path = 'WhitelistedUser.json'
                                if os.path.exists(file_path):
                                    try:
                                        with open(file_path, 'r') as file:
                                            users_data = json.load(file)
                                            user_key = users_data.get(str(user.id), {}).get('key')

                                        if user_key:
                                            data = run_curl_command(url, method='POST', data={"key": user_key})

                                            if data.get('success'):
                                                await update_role_and_key(user.id, remove_role=True)
                                                update_whitelist_file(user.id, user_key, users_data[str(user.id)]['expiration'], users_data[str(user.id)]['reason'], datetime.utcnow())

                                                await interaction.response.send_message(f"Key for user {user.name} has been deleted.", ephemeral=True)
                                            else:
                                                await interaction.response.send_message(f"Failed to delete the key for user {user.name}.", ephemeral=True)
                                        else:
                                            await interaction.response.send_message(f"No key found for user {user.name}.", ephemeral=True)
                                    except (IOError, json.JSONDecodeError) as e:
                                        await interaction.response.send_message(f'Error handling WhitelistedUser.json: {e}', ephemeral=True)
                            except Exception as e:
                                await interaction.response.send_message(f'Error: {e}', ephemeral=True)

                    view = ProfileButtons()
                    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                else:
                    await interaction.followup.send(f"No data found for user {user.name}.", ephemeral=True)
            except (IOError, json.JSONDecodeError) as e:
                await interaction.followup.send(f'Error handling WhitelistedUser.json: {e}', ephemeral=True)
        else:
            await interaction.followup.send("Whitelist file not found.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'Error: {e}', ephemeral=True)

@bot.tree.command(name="reset-hwid", description="Reset HWID for a user")
@app_commands.describe(user="The user to reset HWID")
async def reset_hwid(interaction: discord.Interaction, user: discord.User):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("Thinking...", ephemeral=True)

    try:
        url = "http://localhost:18635/reset-hwid"
        data = run_curl_command(url, method='POST', data={"user_id": user.id})
        
        if data.get('success'):
            embed = discord.Embed(
                title="HWID Reset",
                description=f"**User:**\n{user.name} ({user.id})\n**Status:**\nHWID reset successfully.",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            embed.set_image(url=images["reset_hwid"])

            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f'Failed to reset HWID for user `{user.name}`.', ephemeral=True)
    except ValueError as e:
        await interaction.followup.send(f'Error: {e}', ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'An unexpected error occurred: {e}', ephemeral=True)

@bot.tree.command(name="deletekey", description="Delete a key from the server")
@app_commands.describe(key="The key to delete")
async def delete_key(interaction: discord.Interaction, key: str):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("Thinking...", ephemeral=True)

    try:
        url = "http://localhost:18635/delete-key"
        data = run_curl_command(url, method='POST', data={"key": key})
        
        if data.get('success'):
            file_path = 'WhitelistedUser.json'
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r+') as file:
                        users_data = json.load(file)
                        users_data = {k: v for k, v in users_data.items() if v['key'] != key}
                        file.seek(0)
                        json.dump(users_data, file, indent=4)
                        file.truncate()
                except (IOError, json.JSONDecodeError) as e:
                    print(f'Error handling WhitelistedUser.json: {e}')

            embed = discord.Embed(
                title="Key Service",
                description=f"**Status:**\nKey `{key}` has been deleted.",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            embed.set_image(url=images["delete_key"])

            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f'Failed to delete the key `{key}`.', ephemeral=True)
    except ValueError as e:
        await interaction.followup.send(f'Error: {e}', ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'An unexpected error occurred: {e}', ephemeral=True)

@bot.tree.command(name="help", description="Get information about available commands")
async def help(interaction: discord.Interaction):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    help_message = (
        "**Available Commands:**\n\n"
        "/whitelist - Whitelist a user and generate a key\n"
        "/deletekey - Delete a key from the server\n"
        "/reset-hwid - Reset HWID for a user\n"
        "/profile - Get the profile of a whitelisted user\n"
    )

    embed = discord.Embed(
        title="Help",
        description=help_message,
        color=discord.Color.blue()
    )
    embed.set_image(url=images["help"])

    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(BOT_TOKEN)
