import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True 
bot = commands.Bot(command_prefix="^", intents=intents)

invite_roles = {
    #FLC
    "mxErxHaQHd": [1310901012046938175],
}

@bot.event
async def on_member_join(member):
    guild = member.guild
    updated_invites = await guild.invites()

    # Check which invite was used
    for invite in updated_invites:
        if invite.code in invite_roles:
            role_ids = invite_roles[invite.code]
            for role_id in role_ids:
                role = guild.get_role(role_id)
                if role:
                    await member.add_roles(role)
                    print(f"Assigned role '{role.name}' to {member.name} via invite '{invite.code}'.")
            return

bot.run(TOKEN)