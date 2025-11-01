import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import os
import smtplib
from email.message import EmailMessage
import json
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True 

# env
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
WHATSAPP_URL = os.getenv("WHATSAPP_URL")
CLUSTER_INVITE_URL = "https://discord.gg/g2MHZGpdrc"
ROLE_ID = 1350132344417157140
GOOGLE_SHEET_CSV_URL = os.getenv("GOOGLE_SHEET_CSV_URL")
# google sheets
google_creds = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(google_creds, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_url(GOOGLE_SHEET_CSV_URL).get_worksheet(0)

bot = commands.Bot(command_prefix="^", intents=intents)

invite_roles = {
    #FLC
    "mxErxHaQHd": [1310901012046938175],
    #SOSC Sahyadri
    "vuwSmAdTXU": [1310901365131968543],
    #Dev Nation
    "NbDt3Qkfbw": [1310901438926553149],
    #CoRE,
    "xbQKb6A6": [1310901518106493048], # expired
    #GDG SJEC
    "SwPv7knXkp": [1310930958547030047],
    #Sceptix
    "SwPv7knXkp": [1310901774361563206],
    #Glug Pace
    "2wYqMnuYbs": [1310901583231451137],
    #CLuster Members
    "g2MHZGpdrc": [1350132344417157140]
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

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.tree.sync()
    print("Slash commands synced.")


def send_email(recipient_email: str):
    msg = EmailMessage()
    msg["Subject"] = "🎉 Congratulations! You are selected for DK24 Cluster. 🎉"
    msg["From"] = EMAIL_USER
    msg["To"] = recipient_email

    msg.set_content(
        f"""
<html>
  <body style="font-family: Arial, sans-serif; background-color:#f5f7fa; padding:20px;">
    <div style="max-width:600px; margin:auto; background:white; border-radius:12px; padding:30px; box-shadow:0 4px 12px rgba(0,0,0,0.1);">
      <div style="text-align:center;">
        <img src="https://dk24.org/logo.png" alt="DK24 Logo" width="100" style="margin-bottom:15px;">
        <h2 style="color:#2b2d42;">You're Invited to Join the DK24 Cluster 🎉</h2>
      </div>
      <p style="color:#333; font-size:15px;">
        We’re excited to welcome you to the <b>DK24 Discord Community and DK24 Cluster WhatsApp Group</b> - a collaborative hub for students and developers from partner communities.  
        Click below to join and be part of our amazing network! Once joined use <code>/verify your-email</code> command with your registered email to claim your cluster role.
      </p>
      <div style="text-align:center; margin:30px 0;">
        <a href="{CLUSTER_INVITE_URL}"
           style="background:#5865F2; color:white; text-decoration:none; padding:12px 24px; border-radius:6px; font-weight:bold;">
           Join Discord Server
        </a>
        <a href="{WHATSAPP_URL+recipient_email}"
           style="background:#25D366; color:white; text-decoration:none; padding:12px 24px; border-radius:6px; font-weight:bold; margin-left:10px;">
           Join WhatsApp Group
        </a>
      </div>
      <p style="font-size:13px; color:#555; text-align:center;">
        Please use the <b>/verify</b> command on Discord with your email to claim your cluster role once joined.
      </p>
      <hr style="border:none; border-top:1px solid #eee; margin:20px 0;">
      <p style="text-align:center; font-size:12px; color:#777;">
        DK24 | Connecting College Tech Communities
      </p>
    </div>
  </body>
</html>
""",
        subtype="html",
    )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)
        print(f"✅ Sent invite email to {recipient_email}")


@bot.tree.command(name="invite", description="Send invites to accepted users")
@commands.has_permissions(administrator=True)
async def invite_command(interaction: discord.Interaction):
    await interaction.response.send_message("📨 Processing invites...", ephemeral=True)

    try:
        rows = sheet.get_all_records()
        count = 0

        for i, row in enumerate(rows, start=2):
            print(i, row)
            responded = str(row.get("responded", "")).strip().lower()
            accepted = str(row.get("accepted", "")).strip().lower()
            email = str(row.get("email", "")).strip()

            if responded == "no" and accepted == "yes" and email:
                try:
                    send_email(email)
                    sheet.update_cell(i, list(row.keys()).index("responded") + 1, "yes")
                    count += 1
                except Exception as e:
                    print(f"❌ Failed to send to {email}: {e}")

        await interaction.followup.send(f"✅ Sent {count} invites successfully!", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Failed to process Google Sheet: {e}", ephemeral=True)


@bot.tree.command(name="verify", description="Verify your email to claim your cluster role")
@app_commands.describe(email="Your registered email address")
async def verify_command(interaction: discord.Interaction, email: str):
    await interaction.response.send_message("🔍 Verifying your email...", ephemeral=True)

    try:
        rows = sheet.get_all_records()
        guild = interaction.guild
        member = interaction.user

        for i, row in enumerate(rows, start=2):
            if str(row.get("email", "")).strip().lower() == email.lower():
                claimed = str(row.get("roleClaimed", "")).strip().lower()

                if claimed == "yes":
                    await interaction.followup.send("⚠️ You have already claimed your role.", ephemeral=True)
                    return

                role = guild.get_role(ROLE_ID)
                if role:
                    await member.add_roles(role)
                    sheet.update_cell(i, list(row.keys()).index("roleClaimed") + 1, "yes")
                    await interaction.followup.send("✅ Role successfully claimed!", ephemeral=True)
                    print(f"Assigned role to {member.name}")
                    return

        await interaction.followup.send("❌ Email not found or not eligible.", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Verification failed: {e}", ephemeral=True)

bot.run(TOKEN)