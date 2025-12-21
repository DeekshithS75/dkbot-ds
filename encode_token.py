import base64
import os

if not os.path.exists('key/token.pickle'):
    print("Error: token.pickle not found.")
    print("Please run the main.py script first to generate the token.pickle file.")
else:
    with open('key/token.pickle', 'rb') as token:
        encoded_token = base64.b64encode(token.read()).decode('utf-8')
        print("Copy the following string and add it to your .env file as GMAIL_API_TOKEN_BASE64=")
        print("-" * 20)
        print(encoded_token)
