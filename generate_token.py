import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# The scope for the Gmail API.
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.send']
TOKEN_PICKLE_PATH = 'key/token.pickle'
CREDENTIALS_PATH = 'credentials.json'

def generate_token():
    """
    Generates a new token.pickle file for Gmail API access.
    """
    creds = None

    # Check if token.pickle exists and if it's valid.
    if os.path.exists(TOKEN_PICKLE_PATH):
        with open(TOKEN_PICKLE_PATH, 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Failed to refresh token: {e}")
                print("Proceeding to re-authenticate.")
                creds = None # Force re-authentication
        else:
            creds = None # Force re-authentication

    if not creds:
        if not os.path.exists(CREDENTIALS_PATH):
            print(f"Error: '{CREDENTIALS_PATH}' not found.")
            print("Please download your OAuth 2.0 Client credentials from the Google Cloud Console and save them as 'credentials.json' in the root directory.")
            return

        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_PATH, GMAIL_SCOPES)
        creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        os.makedirs(os.path.dirname(TOKEN_PICKLE_PATH), exist_ok=True)
        with open(TOKEN_PICKLE_PATH, 'wb') as token:
            pickle.dump(creds, token)
        print(f"Token saved to {TOKEN_PICKLE_PATH}")

if __name__ == '__main__':
    generate_token()
