import discord
from discord.ext import commands
from discord import app_commands
import requests
from datetime import datetime, timedelta
import json
import os
import re

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

def calculate_expiration(expiration: str) -> (str, datetime):
    now = datetime.utcnow()
    if expiration.lower() == 'never':
        return 'Never', None
    elif expiration.endswith('d'):
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

@bot.tree.command(name="whitelist", description="Whitelist a user and generate a key")
@app_commands.describe(user="The user to whitelist", expiration="Expiration time (e.g., 1d, 2h, 1m, 30s, never)", reason="Reason for whitelisting")
async def whitelist(interaction: discord.Interaction, user: discord.User, expiration: str = "never", reason: str = "Not Specified"):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    # Send the initial thinking message
    thinking_message = await interaction.response.send_message("Thinking...", ephemeral=True)
    
    try:
        url = "http://localhost:18635/generate-key"
        response = requests.post(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if response.status_code == 200 and data.get('success'):
            new_key = data['key']

            # Calculate expiration date
            now = datetime.utcnow()
            expiration_str = calculate_expiration(expiration, now)

            embed = discord.Embed(
                title="Key Service",
                description=f"**User:**\n{user.name} ({user.id})\n**Status:**\nWhitelisted\n**Key:**\n{new_key}\n**Expiration:**\n{expiration_str}\n**Reason:**\n{reason}",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Requested at {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            embed.set_image(url="https://cdn.pfps.gg/banners/2919-cat.gif")

            try:
                await user.send(embed=embed)
                # Save the user ID and key
                update_whitelist_file(user.id, new_key, expiration_str, reason, now)

                # Add the whitelist role to the user
                guild = interaction.guild
                member = guild.get_member(user.id)
                if member:
                    role = guild.get_role(WHITELIST_ROLE_ID)
                    if role:
                        await member.add_roles(role)
                
                # Send success message to whitelister
                success_embed = discord.Embed(
                    title="Whitelisting Success",
                    description=f"**User:**\n{user.name} ({user.id})\n**Key:**\n{new_key}\n**Expiration:**\n{expiration_str}\n**Reason:**\n{reason}",
                    color=discord.Color.blue()
                )
                success_embed.set_footer(text=f"Requested at {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                success_embed.set_image(url="https://cdn.pfps.gg/banners/2919-cat.gif")
                await interaction.followup.send(embed=success_embed, ephemeral=True)

            except discord.Forbidden:
                await interaction.followup.send(f"Unable to send a DM to {user.name}.", ephemeral=True)
        else:
            await interaction.followup.send('Failed to generate a new key.', ephemeral=True)
    except requests.exceptions.RequestException as e:
        await interaction.followup.send(f'Error: {e}', ephemeral=True)
    except ValueError as e:
        await interaction.followup.send(f'Error parsing JSON: {e}', ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'Unexpected error: {e}', ephemeral=True)

def calculate_expiration(expiration, now):
    if expiration.lower() == 'never':
        return 'Never'
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
        return 'Invalid format'
    return expiration_date.strftime('%Y-%m-%d %H:%M:%S UTC')

def update_whitelist_file(user_id, key, expiration_str, reason, now):
    file_path = 'WhitelistedUser.json'
    try:
        with open(file_path, 'r+') as file:
            users_data = json.load(file)
            users_data[str(user_id)] = {
                "key": key,
                "expiration": expiration_str,
                "reason": reason,
                "created": now.strftime('%Y-%m-%d %H:%M:%S UTC'),
                "status": "Whitelisted"
            }
            file.seek(0)
            json.dump(users_data, file, indent=4)
            file.truncate()  # Make sure to truncate any extra data after the new content
    except Exception as e:
        print(f'Error updating whitelist file: {e}')

@bot.tree.command(name="deletekey", description="Delete a key from the server")
@app_commands.describe(key="The key to delete")
async def delete_key(interaction: discord.Interaction, key: str):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    url = "http://localhost:18635/delete-key"
    try:
        response = requests.post(url, json={"key": key})
        data = response.json()
        if response.status_code == 200 and data.get('success'):
            await interaction.response.send_message(f"Key `{key}` deleted successfully.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Failed to delete key `{key}`.", ephemeral=True)
    except requests.exceptions.RequestException as e:
        await interaction.response.send_message(f'Error: {e}', ephemeral=True)
    except ValueError as e:
        await interaction.response.send_message(f'Error parsing JSON: {e}', ephemeral=True)

@bot.tree.command(name="resethwid", description="Reset HWID for a user")
@app_commands.describe(user="The user whose HWID will be reset")
async def reset_hwid(interaction: discord.Interaction, user: discord.User):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    try:
        # Load whitelisted users
        with open('WhitelistedUser.json', 'r') as file:
            users_data = json.load(file)

        # Get the key for the user
        user_data = users_data.get(str(user.id))

        if user_data:
            user_key = user_data["key"]
            reset_url = "http://localhost:18635/reset-hwid"
            reset_response = requests.post(reset_url, json={"key": user_key}, timeout=30)
            reset_data = reset_response.json()

            if reset_response.status_code == 200 and reset_data.get('success'):
                embed = discord.Embed(
                    title="HWID Reset Successful",
                    description=f"**User:** {user.name}\n**Status:** HWID has been successfully reset.",
                    color=discord.Color.blue()
                )
                embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                embed.set_image(url="https://cdn.pfps.gg/banners/3222-aesthetic-blue.gif")

                # Re-add the whitelist role to the user
                guild = interaction.guild
                member = guild.get_member(user.id)
                if member:
                    role = guild.get_role(WHITELIST_ROLE_ID)
                    if role:
                        await member.add_roles(role)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="HWID Reset Failed",
                    description=f"**User:** {user.name}\n**Status:** Failed to reset HWID.",
                    color=discord.Color.red()
                )
                embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                embed.set_image(url="https://cdn.pfps.gg/banners/3222-aesthetic-blue.gif")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="HWID Reset Failed",
                description=f"No whitelist data found for {user.name}.",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            embed.set_image(url="https://cdn.pfps.gg/banners/3222-aesthetic-blue.gif")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    except requests.exceptions.RequestException as e:
        embed = discord.Embed(
            title="HWID Reset Error",
            description=f'Error during HWID reset: {e}',
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        embed.set_image(url="https://cdn.pfps.gg/banners/3222-aesthetic-blue.gif")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        embed = discord.Embed(
            title="Unexpected Error",
            description=f'Unexpected error: {e}',
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        embed.set_image(url="https://cdn.pfps.gg/banners/3222-aesthetic-blue.gif")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="profile", description="Show your profile information")
async def profile(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    file_path = 'WhitelistedUser.json'
    try:
        # Read user data
        with open(file_path, 'r') as file:
            users_data = json.load(file)
            user_data = users_data.get(user_id, None)
        
        # Debug print
        print("User Data:", user_data)

        if user_data:
            # Fetch HWID data
            hwid_url = "http://localhost:18635/fetch-keys-hwids"
            response = requests.get(hwid_url)
            response.raise_for_status()
            
            # Clean up and parse HWID data
            hwid_data = response.text
            
            # Remove the 'return ' prefix and replace single quotes with double quotes
            hwid_data = re.sub(r"^return\s*", "", hwid_data)
            hwid_data = hwid_data.replace("'", '"')
            
            # Parse the data as JSON
            hwid_data = json.loads(hwid_data)
            
            # Debug print
            print("HWID Data:", hwid_data)

            # Retrieve HWID
            hwid = hwid_data.get(user_data.get("key", ""), "None")
            
            # Create embed message
            embed = discord.Embed(
                title="Profile Information",
                description=f"**User:** {interaction.user.name} ({interaction.user.id})\n"
                            f"**Status:** {user_data.get('status', 'Unknown')}\n"
                            f"**Key:** {user_data.get('key', 'None')}\n"
                            f"**Expiration:** {user_data.get('expiration', 'Unknown')}\n"
                            f"**Reason:** {user_data.get('reason', 'None')}\n"
                            f"**Created:** {user_data.get('created', 'Unknown')}\n"
                            f"**HWID:** {hwid}",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Requested at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            embed.set_image(url="https://cdn.pfps.gg/banners/2919-cat.gif")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("No profile data found.", ephemeral=True)
    except json.JSONDecodeError as e:
        await interaction.response.send_message(f"Error parsing profile data: {e}", ephemeral=True)
    except requests.RequestException as e:
        await interaction.response.send_message(f"Error fetching HWID data: {e}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'Error: {e}', ephemeral=True)

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
