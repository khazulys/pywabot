import secrets
import os

def generate_api_key():
    api_key = secrets.token_hex(32)
    env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')

    print(f"Generated API Key: {api_key}")
    print("\n---")
    print(f"Please add this key to your .env file located at: {env_file_path}")
    print("Add the following line to the file:")
    print(f"PYWABOT_API_KEY={api_key}")
    print("\nIf the .env file does not exist, please create it.")

if __name__ == "__main__":
    generate_api_key()
