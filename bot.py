import discord
from discord.ext import commands
from discord import app_commands, ButtonStyle, Interaction
from discord.ui import Button, View
import subprocess
from datetime import datetime
import json
import os
import time

# Load bot token from SavedToken.json
def load_token():
    with open('SavedToken.json', 'r') as file:
        data = json.load(file)
        return data.get('BOT_TOKEN')

BOT_TOKEN = load_token()

# Check if the token is loaded
if BOT_TOKEN is None:
    raise ValueError("BOT_TOKEN is not set in SavedToken.json.")

intents = discord.Intents.default()
intents.members = True  # Enable the members intent to manage roles
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
        synced = await bot.tree.sync()  # Syncs the commands with Discord
        print(f'Synced {len(synced)} command(s)')
    except Exception as e:
        print(e)

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

def run_curl_command(url: str, method: str = 'GET', data: dict = None) -> dict:
    command = ['curl', '-X', method, url]

    if data:
        command += ['-d', json.dumps(data), '-H', 'Content-Type: application/json']

    retries = 5
    for attempt in range(retries):
        try:
            print(f'Running command: {" ".join(command)}')  # Print the curl command for debugging
            result = subprocess.run(command, capture_output=True, text=True, timeout=2)
            print(f'Command output: {result.stdout}')  # Print the output for debugging
            print(f'Command error: {result.stderr}')  # Print any errors for debugging

            if result.returncode != 0:
                raise Exception(f'curl error: {result.stderr}')

            # Handle the response format
            response = result.stdout.strip()
            if response.startswith("return "):
                response = response[7:]  # Remove "return " prefix

            # Attempt to correct the non-standard JSON format
            corrected_output = response.replace("'", "\"")
            try:
                return json.loads(corrected_output)
            except json.JSONDecodeError:
                raise ValueError(f'Invalid JSON response after correction: {corrected_output}')
        
        except subprocess.TimeoutExpired:
            print(f"Attempt {attempt + 1} of {retries} timed out. Retrying...")
            time.sleep(1)  # Optional: add a small delay before retrying

    raise Exception("Max retries reached. Failed to complete the curl command.")

async def update_role_and_key(user_id: int, remove_role: bool = False):
    guild = discord.utils.get(bot.guilds, id=ALLOWED_GUILD_ID)
    if guild:
        member = guild.get_member(user_id)
        if member:
            role = guild.get_role(WHITELIST_ROLE_ID)
            if role and remove_role:
                await member.remove_roles(role)
                
    # Remove key from storage
    with open('WhitelistedUser.json', 'r+') as file:
        users_data = json.load(file)
        if str(user_id) in users_data:
            del users_data[str(user_id)]
            file.seek(0)
            json.dump(users_data, file, indent=4)
            file.truncate()

def update_whitelist_file(user_id: int, key: str, expiration: str, reason: str, request_time: datetime):
    file_path = 'WhitelistedUser.json'
    
    # Load existing data
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            users_data = json.load(file)
    else:
        users_data = {}

    # Add or update user data
    users_data[str(user_id)] = {
        'key': key,
        'expiration': expiration,
        'reason': reason,
        'created': request_time.strftime('%Y-%m-%d %H:%M:%S UTC'),
        'status': 'Whitelisted'
    }

    # Write updated data back to the file
    with open(file_path, 'w') as file:
        json.dump(users_data, file, indent=4)

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

            # Calculate expiration date
            expiration_str, expiration_date = calculate_expiration(expiration, datetime.utcnow())

            embed = discord.Embed(
                title="Key Service",
                description=f"**User:**\n{user.name} ({user.id})\n**Status:**\nWhitelisted\n**Key:**\n{new_key}\n**Expiration:**\n{expiration_str}\n**Reason:**\n{reason}",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            embed.set_image(url="https://cdn.pfps.gg/banners/2919-cat.gif")

            try:
                await user.send(embed=embed)
                update_whitelist_file(user.id, new_key, expiration_str, reason, datetime.utcnow())

                guild = interaction.guild
                member = guild.get_member(user.id)
                if member:
                    role = guild.get_role(WHITELIST_ROLE_ID)
                    if role:
                        await member.add_roles(role)
                
                success_embed = discord.Embed(
                    title="Whitelisting Success",
                    description=f"**User:**\n{user.name} ({user.id})\n**Status:**\nWhitelisted\n**Key:**\n{new_key}\n**Expiration:**\n{expiration_str}\n**Reason:**\n{reason}",
                    color=discord.Color.blue()
                )
                success_embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                success_embed.set_image(url="https://cdn.pfps.gg/banners/2919-cat.gif")
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
            with open('WhitelistedUser.json', 'r+') as file:
                users_data = json.load(file)
                users_to_remove = [user_id for user_id, info in users_data.items() if info['key'] == key]

                for user_id in users_to_remove:
                    # Remove the key from the file
                    del users_data[user_id]

                    # Remove the whitelist role
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

            await interaction.followup.send(f"Key '{key}' has been deleted and role removed from whitelisted users.", ephemeral=True)
        else:
            await interaction.followup.send(f"Failed to delete the key '{key}'.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'Error: {e}', ephemeral=True)

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

    await interaction.response.send_message("Thinking...", ephemeral=True)

    try:
        with open('WhitelistedUser.json', 'r') as file:
            users_data = json.load(file)
            user_data = users_data.get(str(user.id))

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

            class ResetHWIDButton(View):
                @discord.ui.button(label="Reset HWID", style=ButtonStyle.red)
                async def reset_hwid_button(self, interaction: Interaction, button: Button):
                    if interaction.user.id != user.id and not is_whitelist_admin(interaction.user):
                        await interaction.response.send_message("You do not have permission to reset HWID for this user.", ephemeral=True)
                        return
                    # Directly run reset HWID logic here
                    await self.reset_hwid(interaction, user)

                async def reset_hwid(self, interaction: Interaction, user: discord.User):
                    # Use the `reset_hwid` function here
                    url = "http://localhost:18635/reset-hwid"
                    try:
                        with open('WhitelistedUser.json', 'r') as file:
                            users_data = json.load(file)
                            user_key = users_data.get(str(user.id), {}).get('key')

                        if user_key:
                            data = run_curl_command(url, method='POST', data={"key": user_key})

                            if data.get('success'):
                                # Update the user's HWID status in the whitelist file
                                with open('WhitelistedUser.json', 'r+') as file:
                                    users_data = json.load(file)
                                    if str(user.id) in users_data:
                                        users_data[str(user.id)]['status'] = 'HWID Reset'
                                        file.seek(0)
                                        json.dump(users_data, file, indent=4)
                                        file.truncate()

                                await interaction.response.send_message(f"HWID for user {user.name} has been reset.", ephemeral=True)
                            else:
                                await interaction.response.send_message(f"Failed to reset HWID for user {user.name}.", ephemeral=True)
                        else:
                            await interaction.response.send_message(f"No key found for user {user.name}.", ephemeral=True)
                    except Exception as e:
                        await interaction.response.send_message(f'Error: {e}', ephemeral=True)

            view = ResetHWIDButton()
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.followup.send(f"No data found for user {user.name}.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'Error: {e}', ephemeral=True)

@bot.tree.command(name="resethwid", description="Reset HWID for a user")
@app_commands.describe(user="The user to reset HWID for")
async def reset_hwid(interaction: discord.Interaction, user: discord.User):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    # Send the initial thinking message
    await interaction.response.send_message("Thinking...", ephemeral=True)

    try:
        url = "http://localhost:18635/reset-hwid"
        with open('WhitelistedUser.json', 'r') as file:
            users_data = json.load(file)
            user_key = users_data.get(str(user.id), {}).get('key')

        if user_key:
            data = run_curl_command(url, method='POST', data={"key": user_key})

            if data.get('success'):
                # Update the user's HWID status in the whitelist file
                with open('WhitelistedUser.json', 'r+') as file:
                    users_data = json.load(file)
                    if str(user.id) in users_data:
                        users_data[str(user.id)]['status'] = 'HWID Reset'
                        file.seek(0)
                        json.dump(users_data, file, indent=4)
                        file.truncate()

                await interaction.followup.send(f"HWID for user {user.name} has been reset.", ephemeral=True)
            else:
                await interaction.followup.send(f"Failed to reset HWID for user {user.name}.", ephemeral=True)
        else:
            await interaction.followup.send(f"No key found for user {user.name}.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'Error: {e}', ephemeral=True)

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

