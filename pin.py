import io
import os
import asyncio
import aiohttp
import json
import requests
from pyrogram import Client, filters
from pymongo import MongoClient
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from pyrogram.errors import FloodWait, RPCError, UserNotParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Replace these values with your own credentials
API_ID = '12799559'
API_HASH = '077254e69d93d08357f25bb5f4504580'
BOT_TOKEN = '6525647702:AAEsJ5DYNulz3nwQKQPS57sKVT_mnuEzRRo'
MONGO_URI = 'mongodb://bot:bot@cluster0.8vepzds.mongodb.net/?retryWrites=true&w=majority'
DATABASE_NAME = 'Pinterest_bot'
COLLECTION_NAME = 'users'
CHANNEL_ID = "@codecbots"  # Replace with your channel's username

app = Client("pinterest_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
executor = ThreadPoolExecutor(max_workers=160)
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DATABASE_NAME]
users_collection = db[COLLECTION_NAME]

BOT_URL = "https://pinterestdownloader.xyz"
WEBAPP_URL = "https://t.me/PinterestVideoDlBot/pinterestdl"

# Initialize the userbot client
userbot = Client("userbot", api_id=API_ID, api_hash=API_HASH)

async def check_user_membership(user_id):
    try:
        # Use the userbot to check if the user is in the channel
        chat_member = await userbot.get_chat_member(CHANNEL_ID, user_id)
        print(chat_member)  # Optional logging for debugging

        if chat_member.status in ["member", "administrator", "creator"]:
            return True
        return False
    except Exception as e:
        print(f"Error checking membership via userbot: {e}")
        return False

@app.on_message(filters.command("start") & filters.private)
async def handle_start_command(client, message):
    user_id = message.from_user.id

    # Check if the user is a member of the required channel using the userbot
    is_member = await check_user_membership(user_id)
    if not is_member:
        await message.reply_text(
            f"You need to join [@codecbots]({CHANNEL_ID}) to use this bot.",
            disable_web_page_preview=True
        )
        return  # Stop further execution if not a member

    # Add user to the database if not already there
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id})

    user_count = users_collection.count_documents({})

    instructions = (
        "Welcome! This is **Pinterest Downloader Bot**. This bot can download videos from Pinterest.\n"
        "• Send Pinterest video link, and the bot will download it and send it to you.\n"
        "• If you face any issues, please contact the support chat so developers can fix your issue.\n"
        "• Use the /privacy command to view the privacy policy, and interact with your data.\n"
        "• For more features and better experience, visit our website: [Pinterest Video Downloader]({BOT_URL})\n"
        f"• Number of users on bot: {user_count}\n"
    )
    buttons = [
        [
            InlineKeyboardButton("Pinterest downloader Website", url=BOT_URL),
            InlineKeyboardButton("Support Group", url="https://codecarchive.t.me"),
        ],
        [
            InlineKeyboardButton("Updates", url="https://codecbots.t.me"),
            InlineKeyboardButton("Contact Developer", url="https://t.me/CodecBots/4")
        ],
        [
            InlineKeyboardButton("Launch Pinterest webapp on telegram", url=WEBAPP_URL)
        ]
    ]
    await message.reply_text(instructions, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_message(filters.text & filters.private)
async def handle_message(client, message):
    user_id = message.from_user.id

    # Check if the user is a member of the required channel using the userbot
    is_member = await check_user_membership(user_id)
    if not is_member:
        await message.reply_text(
            f"You need to join [@codecbots]({CHANNEL_ID}) to use this bot.",
            disable_web_page_preview=True
        )
        return  # Stop further execution if not a member

    url = message.text
    if "pinterest.com" in url or "pin.it" in url:
        try:
            if "pin.it" in url:
                url = await asyncio.get_event_loop().run_in_executor(executor, expand_shortened_url, url)
            
            asyncio.create_task(download_and_send_video(client, message, url))
        except FloodWait as e:
            await asyncio.sleep(e.x)
        except Exception as e:
            await message.reply_text(f"An error occurred while processing your request. Please try again later or visit our [website]({BOT_URL})", disable_web_page_preview=True)
    else:
        await message.reply_text(f"Please provide a valid Pinterest video link. For more features, visit our [website]({BOT_URL})", disable_web_page_preview=True)

@app.on_message(filters.command("broadcast") & filters.user([1137799257]))  # Add your user ID to SUDOERS
async def broadcast_message(client, message):
    if message.reply_to_message:
        broadcast_message = message.reply_to_message.text
    else:
        if len(message.command) < 2:
            await message.reply_text("Usage: /broadcast <message>")
            return
        broadcast_message = message.text.split(None, 1)[1]

    all_users = users_collection.find()
    broadcast_count = 0

    for user in all_users:
        try:
            await client.send_message(user['user_id'], broadcast_message)
            broadcast_count += 1
            await asyncio.sleep(0.1)  # To prevent hitting the flood limit
        except FloodWait as e:
            await asyncio.sleep(e.x)
        except RPCError as e:
            return
        except Exception as e:
            await message.reply_text(f"Error broadcasting to user {user['user_id']}: {e}")

    await message.reply_text(f"Broadcast completed. Message sent to {broadcast_count} users.")

# Utility functions

def expand_shortened_url(url):
    try:
        response = requests.head(url, allow_redirects=True)
        final_url = response.url
        return final_url
    except Exception as e:
        return url

async def fetch_video(session, url):
    async with session.get(url) as response:
        return await response.read()
        
async def download_and_send_video(client, message, url):
    try:
        video_url = await asyncio.get_event_loop().run_in_executor(executor, get_pinterest_video_url, url)
        if not video_url:
            await message.reply_text(
                f"Could not find a video at the provided link. For more features, visit our [website]({BOT_URL})", 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Web App", url=WEBAPP_URL)]])
            )
            return
        
        async with aiohttp.ClientSession() as session:
            video_data = await fetch_video(session, video_url)
        
        video_io = io.BytesIO(video_data)
        
        await client.send_video(
            chat_id=message.chat.id,
            video=video_io,
            file_name="PinterestVideoDlBot.mp4",  
            caption=f"•Uploaded By : @PinterestVideoDlBot.\n •For more features and download without limits, use our [website]({BOT_URL}).\n",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Open website on telegram", url=WEBAPP_URL)]])
        )
        
    except Exception as e:
        await message.reply_text(
            f"An error occurred while processing your request. Please try again later or visit our [website]({BOT_URL})", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Web App", url=WEBAPP_URL)]])
        )
    finally:
        await asyncio.sleep(0.1)

def get_pinterest_video_url(pin_url):
    try:
        response = requests.get(pin_url, allow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup.find_all('script', type='application/ld+json'):
            json_data = json.loads(script.string)
            if '@type' in json_data and json_data['@type'] == 'VideoObject':
                video_url = json_data['contentUrl']
                return video_url
    except Exception as e:
        return None

# Start both the userbot and the regular bot
if __name__ == "__main__":
    userbot.start()
    app.run()
