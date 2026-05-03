import asyncio
import datetime
import logging
import math
import os
import traceback
import aiomysql
import discord
from discord.ext import commands
import jpholiday

SERVICE_NAME = "UDC_Announce"
TOKEN = os.getenv("TOKEN")
ANNOUNCE_CHANNEL_ID = int(os.environ.get("ANNOUNCE_CHANNEL_ID"))
TEST_CHANNEL_ID = int(os.environ.get("TEST_CHANNEL_ID"))
BOARD_MEMBER_CHANNEL_ID = int(os.environ.get("BOARD_MEMBER_CHANNEL_ID"))
ALERT_CHANNEL_ID = int(os.environ.get("ALERT_CHANNEL_ID"))

# ログの設定
format = logging.Formatter(
    "{asctime} {levelname:<8} {name}: {message}",
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
