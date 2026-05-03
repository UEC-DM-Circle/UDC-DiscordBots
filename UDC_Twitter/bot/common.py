import asyncio
import datetime
import logging
import os
import sys
import traceback
import aiohttp
import aiomysql
import discord
from discord.ext import commands

SERVICE_NAME = "UDC_Twitter"
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
TWITTER_USER_ID = os.getenv("TWITTER_USER_ID")
GET_TWEET_NUMBER = 5

# ログの設定
format = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
)
handler = logging.StreamHandler()
handler.setFormatter(format)
logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
bot_logger = logging.getLogger(SERVICE_NAME)


async def write_log_message(message: str, category: str):
    if category == "INFO":
        bot_logger.info(message)
    elif category == "ERROR":
        bot_logger.error(message)
    else:
        bot_logger.warning(message)
