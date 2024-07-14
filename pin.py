import io
import os
import asyncio
import aiohttp
import json
import logging
import requests
from pyrogram import Client, filters
from pymongo import MongoClient
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from pyrogram.errors import FloodWait, BadRequest
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

SUDOERS = [1137799257]  
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = '12799559'
API_HASH = '077254e69d93d08357f25bb5f4504580'
BOT_TOKEN = '6525647702:AAEcBZ4z-nkG161VkOPOQOFsNidoao-jwHw'
MONGO_URI = 'mongodb+srv://bot:bot@cluster0.8vepzds.mongodb.net/?retryWrites=true&w=majority'
DATABASE_NAME = 'Pinterest_bot'
COLLECTION_NAME = 'users'

app = Client("pinterest_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
executor = ThreadPoolExecutor(max_workers=160)
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DATABASE_NAME]
users_collection = db[COLLECTION_NAME]

privacy_responses = {
    "info_collect": "We collect the following user data:\n- First Name\n- Last Name\n- Username\n- User ID\n These are public Telegram details that everyone can see.",
    "why_collect": "The collected data is used solely for improving your experience with the bot and for processing the bot stats and to avoid spammers.",
    "what_we_do": "We use the data to personalize your experience and provide better services.",
    "what_we_do_not_do": "We do not share your data with any third parties.",
    "right_to_process": "You have the right to access, correct, or delete your data. [Contact us](t.me/drxew) for any privacy-related inquiries."
}

@app.on_message(filters.command("privacy"))
async def privacy_command(client, message):
    privacy_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Privacy Policy", callback_data="privacy_policy")]]
    )
    await message.reply_text("Select one of the below options for more information about how the bot handles your privacy.", reply_markup=privacy_button)

@app.on_callback_query()
async def handle_callback_query(client, callback_query: CallbackQuery):
    data = callback_query.data
    if data == "privacy_policy":
        buttons = [
            [InlineKeyboardButton("What Information We Collect", callback_data="info_collect")],
            [InlineKeyboardButton("Why We Collect", callback_data="why_collect")],
            [InlineKeyboardButton("What We Do", callback_data="what_we_do")],
            [InlineKeyboardButton("What We Do Not Do", callback_data="what_we_do_not_do")],
            [InlineKeyboardButton("Right to Process", callback_data="right_to_process")]
        ]
        await callback_query.message.edit_text(
            "Our contact details \n Name: PinterestVideoDlBot \n Telegram: https://t.me/CodecArchive \n The bot has been made to protect and preserve privacy as best as possible. \n  Our privacy policy may change from time to time. If we make any material changes to our policies, we will place a prominent notice on https://t.me/CodecBots.", 
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif data in privacy_responses:
        back_button = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Back", callback_data="privacy_policy")]]
        )
        await callback_query.message.edit_text(privacy_responses[data], reply_markup=back_button)
        
@app.on_message(filters.command("start") & filters.private)
async def handle_start_command(client, message):
    user_id = message.from_user.id
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id})
    
    user_count = users_collection.count_documents({})
    
    instructions = (
        "Welcome! This is **Pinterest Downloader Bot**. This bot can download videos from Pinterest.\n"
        "• Send Pinterest video link, and the bot will download it and send it to you.\n"
        "• If you face any issues, please contact the support chat so developers can fix your issue.\n"
        "• Use the /privacy command to view the privacy policy, and interact with your data.\n"
        f"• Number of users on bot: {user_count}\n"
    )
    buttons = [
        [
            InlineKeyboardButton("Support Group", url="https://codecarchive.t.me"),
            InlineKeyboardButton("Updates", url="https://codecbots.t.me"),
        ],
        [
            InlineKeyboardButton("Contact Developer", url="https://t.me/CodecBots/4")
        ]
    ]
    await message.reply_text(instructions, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_message(filters.command("broadcast") & filters.user(SUDOERS))
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
        except Exception as e:
            logger.error(f"Error broadcasting to user {user['user_id']}: {e}")
    
    await message.reply_text(f"Broadcast completed. Message sent to {broadcast_count} users.")

def expand_shortened_url(url):
    try:
        response = requests.head(url, allow_redirects=True)
        final_url = response.url
        return final_url
    except Exception as e:
        logger.error(f"Error expanding URL: {e}")
        return url

def get_pinterest_video_url(pin_url):
    try:
        response = requests.get(pin_url, allow_redirects=True)
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info(f"Response content: {soup.prettify()[:2000]}") 
        for script in soup.find_all('script', type='application/ld+json'):
            json_data = json.loads(script.string)
            logger.info(f"Found JSON-LD script: {json.dumps(json_data, indent=2)[:1000]}")
            if '@type' in json_data and json_data['@type'] == 'VideoObject':
                video_url = json_data['contentUrl']
                logger.info(f"Found video URL: {video_url}")
                return video_url
    except Exception as e:
        logger.error(f"Error getting video URL: {e}")
    return None

async def fetch_video(session, url):
    async with session.get(url) as response:
        return await response.read()
        
async def download_and_send_video(client, message, url):
    try:
        video_url = await asyncio.get_event_loop().run_in_executor(executor, get_pinterest_video_url, url)
        if not video_url:
            await message.reply_text("Could not find a video at the provided link.")
            return
        
        async with aiohttp.ClientSession() as session:
            video_data = await fetch_video(session, video_url)
        
        video_io = io.BytesIO(video_data)
        
        await client.send_video(
            chat_id=message.chat.id,
            video=video_io,
            file_name="PinterestVideoDlBot.mp4",  
            caption="•**__Uploaded By : @PinterestVideoDlBot__**"
        )
        
    except Exception as e:
        logger.error(f"Error in download_and_send_video: {e}")
        await message.reply_text("An error occurred while processing your request.")
    finally:
        await asyncio.sleep(0.1)

@app.on_message(filters.text & filters.private)
async def handle_message(client, message):
    url = message.text
    if "pinterest.com" in url or "pin.it" in url:
        try:
            if "pin.it" in url:
                url = await asyncio.get_event_loop().run_in_executor(executor, expand_shortened_url, url)
            
            asyncio.create_task(download_and_send_video(client, message, url))
        except FloodWait as e:
            logger.warning(f"FloodWait error: Waiting for {e.x} seconds")
            await asyncio.sleep(e.x)
        except Exception as e:
            logger.error(f"Unhandled error: {e}")
            await message.reply_text("An error occurred while processing your request.")
    else:
        await message.reply_text("Please provide a valid Pinterest video link.")

import subprocess

def synchronize_time():
    try:
        # Synchronize system time
        subprocess.run(["sudo", "timedatectl", "set-ntp", "true"], check=True)
        subprocess.run(["sudo", "ntpdate", "-u", "pool.ntp.org"], check=True)
        subprocess.run(["sudo", "hwclock", "--systohc"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Time synchronization failed: {e}")

if __name__ == "__main__":
    try:
        synchronize_time()
        app.run()
    except BadRequest as e:
        logger.error(f"BadRequest error: {e}")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
