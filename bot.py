import discord
from discord.ext import commands
from discord import app_commands
import requests
from datetime import datetime, timedelta
import json
import os

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

# Cute image URL
cute_image = "https://cdn.pfps.gg/banners/2919-cat.gif"

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

@bot.tree.command(name="whitelist", description="Whitelist a user and generate a key")
@app_commands.describe(user="The user to whitelist", expiration="Expiration time (e.g., 1d, 2h, 1m, 30s, never)", reason="Reason for whitelisting")
async def whitelist(interaction: discord.Interaction, user: discord.User, expiration: str = "never", reason: str = "Not Specified"):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.", ephemeral=True)
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    url = "https://joint-marten-virtually.ngrok-free.app/generate-key"
    try:
        response = requests.post(url)
        data = response.json()
        if response.status_code == 200 and data.get('success'):
            new_key = data['key']

            # Calculate expiration date
            now = datetime.utcnow()
            if expiration.lower() == 'never':
                expiration_str = 'Never'
            elif expiration.endswith('d'):
                days = int(expiration[:-1])
                expiration_date = now + timedelta(days=days)
                expiration_str = expiration_date.strftime('%Y-%m-%d %H:%M:%S UTC')
            elif expiration.endswith('h'):
                hours = int(expiration[:-1])
                expiration_date = now + timedelta(hours=hours)
                expiration_str = expiration_date.strftime('%Y-%m-%d %H:%M:%S UTC')
            elif expiration.endswith('m'):
                minutes = int(expiration[:-1])
                expiration_date = now + timedelta(minutes=minutes)
                expiration_str = expiration_date.strftime('%Y-%m-%d %H:%M:%S UTC')
            elif expiration.endswith('s'):
                seconds = int(expiration[:-1])
                expiration_date = now + timedelta(seconds=seconds)
                expiration_str = expiration_date.strftime('%Y-%m-%d %H:%M:%S UTC')
            else:
                expiration_str = 'Invalid format'

            embed = discord.Embed(
                title="Key Service",
                description=f"**User:**\n{user.name} ({user.id})\n**Status:**\nWhitelisted\n**Key:**\n{new_key}\n**Expiration:**\n{expiration_str}\n**Reason:**\n{reason}",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Requested at {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            embed.set_image(url=cute_image)

            try:
                await user.send(embed=embed)
                await interaction.response.send_message(f"I've sent the key to {user.name}'s DMs.", ephemeral=True)

                # Save the user ID and key
                with open('WhitelistedUser.json', 'r+') as file:
                    users_data = json.load(file)
                    users_data[str(user.id)] = new_key
                    file.seek(0)
                    json.dump(users_data, file, indent=4)

                # Add the whitelist role to the user
                guild = interaction.guild
                member = guild.get_member(user.id)
                if member:
                    role = guild.get_role(WHITELIST_ROLE_ID)
                    if role:
                        await member.add_roles(role)
            except discord.Forbidden:
                await interaction.response.send_message(f"Unable to send a DM to {user.name}.", ephemeral=True)
        else:
            await interaction.response.send_message('Failed to generate a new key.', ephemeral=True)
    except requests.exceptions.RequestException as e:
        await interaction.response.send_message(f'Error: {e}', ephemeral=True)
    except ValueError as e:
        await interaction.response.send_message(f'Error parsing JSON: {e}', ephemeral=True)
        
@bot.tree.command(name="deletekey", description="Delete a key from the server")
@app_commands.describe(key="The key to delete")
async def delete_key(interaction: discord.Interaction, key: str):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.")
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.")
        return

    url = "https://joint-marten-virtually.ngrok-free.app/delete-key"
    try:
        response = requests.post(url, json={"key": key})
        data = response.json()
        if response.status_code == 200 and data.get('success'):
            await interaction.response.send_message(f"Key `{key}` deleted successfully.")
        else:
            await interaction.response.send_message(f"Failed to delete key `{key}`.")
    except requests.exceptions.RequestException as e:
        await interaction.response.send_message(f'Error: {e}')
    except ValueError as e:
        await interaction.response.send_message(f'Error parsing JSON: {e}')

@bot.tree.command(name="resethwid", description="Reset HWID for the whitelisted user")
@app_commands.describe(user="The user whose HWID will be reset")
async def reset_hwid(interaction: discord.Interaction, user: discord.User):
    if interaction.guild.id != ALLOWED_GUILD_ID:
        await interaction.response.send_message("This command can only be used in the specified server.")
        return

    if not is_whitelist_admin(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.")
        return

    try:
        # Load whitelisted users
        with open('WhitelistedUser.json', 'r') as file:
            users_data = json.load(file)

        # Get the key for the user
        user_key = users_data.get(str(user.id))

        if user_key:
            reset_url = "https://joint-marten-virtually.ngrok-free.app/reset-hwid"
            reset_response = requests.post(reset_url, json={"key": user_key})
            reset_data = reset_response.json()

            if reset_response.status_code == 200 and reset_data.get('success'):
                await interaction.response.send_message(f"HWID for key `{user_key}` reset successfully.")

                # Re-add the whitelist role to the user
                guild = interaction.guild
                member = guild.get_member(user.id)
                if member:
                    role = guild.get_role(WHITELIST_ROLE_ID)
                    if role:
                        await member.add_roles(role)
            else:
                await interaction.response.send_message(f"Failed to reset HWID for key `{user_key}`. Error: {reset_data.get('message')}")
        else:
            await interaction.response.send_message(f"No key found for user `{user.mention}`.")
    except requests.exceptions.RequestException as e:
        await interaction.response.send_message(f'Error: {e}')
    except ValueError as e:
        await interaction.response.send_message(f'Error parsing JSON: {e}')
    except Exception as e:
        await interaction.response.send_message(f'Unexpected error: {e}')
# Run the bot with the token from the JSON file
bot.run(BOT_TOKEN)
