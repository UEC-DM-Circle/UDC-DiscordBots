import asyncio
import datetime
import logging
import math
import os
import sys
import traceback
import discord
from discord.ext import commands
import aiomysql
import jpholiday

TOKEN = os.getenv("TOKEN")
ANNOUNCE_CHANNEL_ID = int(os.environ.get("ANNOUNCE_CHANNEL_ID"))
TEST_CHANNEL_ID = int(os.environ.get("TEST_CHANNEL_ID"))
BOARD_MEMBER_CHANNEL_ID = int(os.environ.get("BOARD_MEMBER_CHANNEL_ID"))
ALERT_CHANNEL_ID = int(os.environ.get("ALERT_CHANNEL_ID"))
SERVICE_NAME = "UDC_Announce"
format = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}",
    datefmt="%Y-%m-%d %H:%M:%S",
    style="{",
)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(format)
discord.utils.setup_logging(level=logging.INFO, handler=handler)
bot_logger = logging.getLogger(SERVICE_NAME)


async def write_log_message(message: str, category: str):
    if category == "INFO":
        bot_logger.info(message)
    elif category == "ERROR":
        bot_logger.error(message)
    else:
        bot_logger.warning(message)
