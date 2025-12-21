import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging

import config
from google_sheets_client import GoogleSheetsClient
import email_sender
import web_server

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Bot Setup ---
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="^", intents=intents)

# --- Globals ---
# Initialize the Google Sheets client
try:
    sheets_client = GoogleSheetsClient()
except Exception as e:
    logging.critical(f"FATAL: Could not initialize GoogleSheetsClient. The bot will not run. Error: {e}")
    exit()

# --- Interactive UI (Buttons) ---
class ApprovalView(discord.ui.View):
    def __init__(self, applicant_email: str, applicant_name: str):
        super().__init__(timeout=None)  # Persistent view
        self.applicant_email = applicant_email
        self.applicant_name = applicant_name

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id="approve_button")
    async def approve_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Send email
        email_sent = email_sender.send_invite_email(self.applicant_email, self.applicant_name)
        
        if email_sent:
            # Update Google Sheet
            sheets_client.update_status_by_email(self.applicant_email, "yes")
            feedback_message = f"✅ **Approved and sent invite to {self.applicant_name} ({self.applicant_email}).**"
            log_message = f"Admin '{interaction.user.name}' approved {self.applicant_name}."
            new_embed_color = discord.Color.green()
        else:
            feedback_message = f"❌ **Failed to send email to {self.applicant_name} ({self.applicant_email}).** Check logs for details."
            log_message = f"Admin '{interaction.user.name}' attempted to approve {self.applicant_name}, but email failed."
            new_embed_color = discord.Color.orange()

        logging.info(log_message)
        await interaction.followup.send(feedback_message, ephemeral=True)

        # Edit original message to show it's been handled
        original_embed = interaction.message.embeds[0]
        new_embed = original_embed.copy()
        new_embed.color = new_embed_color
        new_embed.set_footer(text=f"Action taken by {interaction.user.name}")
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(embed=new_embed, view=self)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, custom_id="reject_button")
    async def reject_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Update Google Sheet
        sheets_client.update_status_by_email(self.applicant_email, "no")
        
        log_message = f"Admin '{interaction.user.name}' rejected {self.applicant_name}."
        logging.info(log_message)
        
        await interaction.followup.send(f"🗑️ **Rejected {self.applicant_name} ({self.applicant_email}).**", ephemeral=True)

        # Edit original message
        original_embed = interaction.message.embeds[0]
        new_embed = original_embed.copy()
        new_embed.color = discord.Color.red()
        new_embed.set_footer(text=f"Rejected by {interaction.user.name}")

        # Create a new RejectedView
        rejected_view = RejectedView(applicant_email=self.applicant_email, applicant_name=self.applicant_name, original_embed=original_embed)

        await interaction.message.edit(embed=new_embed, view=rejected_view)

class RejectedView(discord.ui.View):
    def __init__(self, applicant_email: str, applicant_name: str, original_embed: discord.Embed):
        super().__init__(timeout=None)
        self.applicant_email = applicant_email
        self.applicant_name = applicant_name
        self.original_embed = original_embed

    @discord.ui.button(label="Changed my mind", style=discord.ButtonStyle.secondary, custom_id="undo_reject_button")
    async def undo_reject_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Revert Google Sheet status
        sheets_client.update_status_by_email(self.applicant_email, "pending")

        log_message = f"Admin '{interaction.user.name}' reverted rejection for {self.applicant_name}."
        logging.info(log_message)

        await interaction.followup.send(f"↩️ **Reverted rejection for {self.applicant_name}.** You can now approve or reject them again.", ephemeral=True)

        # Create a new ApprovalView
        approval_view = ApprovalView(applicant_email=self.applicant_email, applicant_name=self.applicant_name)

        # Edit the message to show the original embed and the new view
        await interaction.message.edit(embed=self.original_embed, view=approval_view)

# --- Bot Events ---
@bot.event
async def on_ready():
    logging.info(f"✅ Logged in as {bot.user}")
    
    # Add the post_approval_card function to the bot instance so the web server can call it
    bot.post_approval_card = post_approval_card
    bot.post_college_applicant_card = post_college_applicant_card
    
    # Start the web server
    await web_server.start_web_server(bot, sheets_client)
    
    # Sync slash commands
    await bot.tree.sync(guild=discord.Object(id=config.GUILD_ID))
    logging.info("Slash commands synced.")

async def post_approval_card(data: dict):
    """Formats and sends the interactive approval message to the admin channel."""
    channel = bot.get_channel(config.ADMIN_CHANNEL_ID)
    if not channel:
        logging.error(f"Could not find admin channel with ID {config.ADMIN_CHANNEL_ID}")
        return

    # Extract data with defaults
    first_name = data.get(config.COL_FIRST_NAME, "N/A")
    last_name = data.get(config.COL_LAST_NAME, "")
    email = data.get(config.COL_EMAIL, "N/A")
    phone = data.get(config.COL_PHONE, "N/A")
    college = data.get(config.COL_COLLEGE, "N/A")
    year = data.get(config.COL_YEAR, "N/A")
    interests = data.get(config.COL_INTERESTS, "N/A")
    motivation = data.get(config.COL_MOTIVATION, "N/A")
    full_name = f"{first_name} {last_name}".strip()

    embed = discord.Embed(
        title="New Individual Entry Added",
        description="──────────────────────────────",
        color=discord.Color.blue()
    )
    embed.add_field(name="👤 Name", value=full_name, inline=False)
    embed.add_field(name="📧 Email", value=email, inline=False)
    embed.add_field(name="📱 Phone", value=phone, inline=False)
    embed.add_field(name="🏫 College", value=college, inline=False)
    embed.add_field(name="📅 Year", value=year, inline=False)
    embed.add_field(name="✨ Interests", value=interests, inline=False)
    embed.add_field(name="💡 Motivation", value=motivation, inline=False)

    view = ApprovalView(applicant_email=email, applicant_name=full_name)
    await channel.send(embed=embed, view=view)


async def post_college_applicant_card(data: dict):
    """Formats and sends the college applicant info to the admin channel."""
    channel = bot.get_channel(config.ADMIN_CHANNEL_ID)
    if not channel:
        logging.error(f"Could not find admin channel with ID {config.ADMIN_CHANNEL_ID}")
        return

    # Extract data with defaults
    college_name = data.get(config.COL_COLLEGE_NAME, "N/A")
    community_name = data.get(config.COL_COMMUNITY_NAME, "N/A")
    rep_name = data.get(config.COL_REP_NAME, "N/A")
    rep_position = data.get(config.COL_REP_POSITION, "N/A")
    rep_email = data.get(config.COL_REP_EMAIL, "N/A")
    rep_phone = data.get(config.COL_REP_PHONE, "N/A")
    faculty_name = data.get(config.COL_FACULTY_NAME, "N/A")
    faculty_email = data.get(config.COL_FACULTY_EMAIL, "N/A")
    community_size = data.get(config.COL_COMMUNITY_SIZE, "N/A")
    community_activities = data.get(config.COL_COMMUNITY_ACTIVITIES, "N/A")
    expectations = data.get(config.COL_EXPECTATIONS, "N/A")

    embed = discord.Embed(
        title="New Community Entry Added",
        description="──────────────────────────────",
        color=discord.Color.purple()
    )
    embed.add_field(name="College", value=college_name, inline=False)
    embed.add_field(name="Community", value=community_name, inline=False)
    embed.add_field(name="Representative", value=f"{rep_name} ({rep_position})", inline=False)
    embed.add_field(name="Rep Email", value=rep_email, inline=False)
    embed.add_field(name="Rep Phone", value=rep_phone, inline=False)
    embed.add_field(name="‍Faculty", value=faculty_name, inline=False)
    embed.add_field(name="Faculty Email", value=faculty_email, inline=False)
    embed.add_field(name="Community Size", value=community_size, inline=False)
    embed.add_field(name="Activities", value=community_activities, inline=False)
    embed.add_field(name="Expectations", value=expectations, inline=False)
    
    await channel.send(embed=embed)


# --- New Admin Slash Commands ---
@bot.tree.command(name="status", description="Get a summary of applicant statuses.", guild=discord.Object(id=config.GUILD_ID))
@commands.has_permissions(administrator=True)
async def status_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    stats = sheets_client.get_stats()
    embed = discord.Embed(title="Applicant Status Summary", color=discord.Color.dark_gold())
    embed.add_field(name="Approved", value=stats['approved'], inline=True)
    embed.add_field(name="Rejected", value=stats['rejected'], inline=True)
    embed.add_field(name="Pending", value=stats['pending'], inline=True)
    embed.set_footer(text=f"Total Applicants: {stats['total']}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="invite", description="Send invites to accepted users")
@commands.has_permissions(administrator=True)
async def invite_command(interaction: discord.Interaction):
    await interaction.response.send_message("📨 Processing invites...")

    try:
        rows = sheets_client.get_all_records()
        count = 0
        total = 0

        for i, row in enumerate(rows, start=2):
            responded = str(row.get("responded", "")).strip().lower()
            accepted = str(row.get("accepted", "")).strip().lower()
            email = str(row.get("email", "")).strip()

            if responded == "no" and accepted == "yes" and email:
                try:
                    total += 1
                    email_sender.send_invite_email(email, row.get("firstName", "")+" "+row.get("lastName", ""))
                    sheets_client.update_cell(i, list(row.keys()).index("responded") + 1, "yes")
                    count += 1
                except Exception as e:
                    print(f"❌ Failed to send to {email}: {e}")

        await interaction.followup.send(f"✅ Sent {count}/{total} invites successfully!")

    except Exception as e:
        await interaction.followup.send(f"❌ Failed to process Google Sheet: {e}")



@bot.tree.command(name="view", description="View applicants by status.", guild=discord.Object(id=config.GUILD_ID))
@app_commands.describe(status="The status of applicants to view.")
@app_commands.choices(status=[
    app_commands.Choice(name="Approved", value="approved"),
    app_commands.Choice(name="Rejected", value="rejected"),
    app_commands.Choice(name="Pending", value="pending"),
])
@commands.has_permissions(administrator=True)
async def view_command(interaction: discord.Interaction, status: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    
    records = sheets_client.get_records_by_status(status.value)
    
    if not records:
        await interaction.followup.send(f"No applicants found with status: {status.name}", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"Applicants: {status.name}",
        color=discord.Color.blue()
    )
    
    description = ""
    for record in records[:25]: # Limit to 25 to avoid hitting Discord's embed limits
        name = f"{record.get(config.COL_FIRST_NAME, '')} {record.get(config.COL_LAST_NAME, '')}".strip()
        email = record.get(config.COL_EMAIL, 'N/A')
        description += f"**{name}** - {email}\n"
        
    embed.description = description
    
    if len(records) > 25:
        embed.set_footer(text=f"Showing 25 of {len(records)} records.")
        
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="search", description="Search for an applicant by name or email.", guild=discord.Object(id=config.GUILD_ID))
@app_commands.describe(query="The name or email to search for.")
@commands.has_permissions(administrator=True)
async def search_command(interaction: discord.Interaction, query: str):
    await interaction.response.defer(ephemeral=True)
    
    records = sheets_client.search_records(query)
    
    if not records:
        await interaction.followup.send(f"No applicants found matching '{query}'.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"Search Results for '{query}'",
        color=discord.Color.blue()
    )
    
    description = ""
    for record in records[:25]: # Limit to 25 to avoid hitting Discord's embed limits
        name = f"{record.get(config.COL_FIRST_NAME, '')} {record.get(config.COL_LAST_NAME, '')}".strip()
        email = record.get(config.COL_EMAIL, 'N/A')
        status = str(record.get(config.COL_ACCEPTED, 'N/A')).strip().lower()
        description += f"**{name}** - {email} - Status: `{status}`\n"
        
    embed.description = description
    
    if len(records) > 25:
        embed.set_footer(text=f"Showing 25 of {len(records)} records.")
        
    await interaction.followup.send(embed=embed, ephemeral=True)


# --- Existing Commands (Refactored) ---
@bot.tree.command(name="verify", description="Verify your email to claim your cluster role", guild=discord.Object(id=config.GUILD_ID))
@app_commands.describe(email="Your registered email address")
async def verify_command(interaction: discord.Interaction, email: str):
    await interaction.response.send_message("🔍 Verifying your email...", ephemeral=True)
    
    record = sheets_client.get_record_by_email(email)
    if not record:
        await interaction.followup.send("❌ Email not found or not eligible.", ephemeral=True)
        return

    if str(record.get(config.COL_ROLE_CLAIMED, "")).strip().lower() == "yes":
        await interaction.followup.send("⚠️ You have already claimed your role.", ephemeral=True)
        return
    
    if str(record.get(config.COL_ACCEPTED, "")).strip().lower() != "yes":
        await interaction.followup.send("❌ Your application has not been approved yet.", ephemeral=True)
        return

    role = interaction.guild.get_role(config.VERIFY_ROLE_ID)
    if role:
        await interaction.user.add_roles(role)
        sheets_client.claim_role_by_email(email)
        logging.info(f"Role '{role.name}' assigned to {interaction.user.name} and sheet updated for {email}.")
        await interaction.followup.send("✅ Role successfully claimed!", ephemeral=True)
    else:
        await interaction.followup.send("❌ Internal error: Could not find the role to assign.", ephemeral=True)

if __name__ == "__main__":
    bot.run(config.TOKEN)
