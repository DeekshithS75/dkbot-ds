import os
from dotenv import load_dotenv

load_dotenv()

# --- Discord Bot ---
TOKEN = os.getenv("TOKEN")
ADMIN_CHANNEL_ID = 1406306662826119449
GUILD_ID = 1304508522305683496

# --- Webhook ---
WEBHOOK_SECRET_KEY = os.getenv("WEBHOOK_SECRET_KEY", "default-secret-key-please-change")
WEB_SERVER_PORT = int(os.getenv("PORT", 8080))

# --- Google Sheets ---
SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_CSV_URL")
GOOGLE_SERVICE_ACCOUNT_EMAIL = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL")
GOOGLE_PRIVATE_KEY = os.getenv("GOOGLE_PRIVATE_KEY")

# --- Gmail API ---
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.send']
# Path inside the project directory to store the generated token.pickle
GMAIL_TOKEN_PICKLE_PATH = 'key/token.pickle'
# Base64 encoded token for initial setup, loaded from env
GMAIL_API_TOKEN_BASE64 = os.getenv("GMAIL_API_TOKEN_BASE64")
SENDER_EMAIL = "me" # Uses the authenticated user's email

# --- Invite Content ---
WHATSAPP_URL = os.getenv("WHATSAPP_URL")
CLUSTER_INVITE_URL = "https://discord.gg/g2MHZGpdrc"
# Role to be assigned upon successful /verify
VERIFY_ROLE_ID = "1350132344417157140"

# --- Column Names ---
COL_EMAIL = "email"
COL_FIRST_NAME = "firstName"
COL_LAST_NAME = "lastName"
COL_PHONE = "phone"
COL_COLLEGE = "college"
COL_YEAR = "year"
COL_INTERESTS = "interests"
COL_MOTIVATION = "motivation"
COL_ACCEPTED = "accepted"
COL_RESPONDED = "responded"
COL_ROLE_CLAIMED = "roleClaimed"

# --- College Application Column Names ---
COL_COLLEGE_NAME = "collegeName"
COL_COMMUNITY_NAME = "communityName"
COL_REP_NAME = "repName"
COL_REP_POSITION = "repPosition"
COL_REP_EMAIL = "repEmail"
COL_REP_PHONE = "repPhone"
COL_FACULTY_NAME = "facultyName"
COL_FACULTY_EMAIL = "facultyEmail"
COL_COMMUNITY_SIZE = "communitySize"
COL_COMMUNITY_ACTIVITIES = "communityActivities"
COL_EXPECTATIONS = "expectations"
