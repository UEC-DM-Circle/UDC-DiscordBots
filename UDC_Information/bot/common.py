import asyncio
import io
import logging
import os
import sys
import socket
import traceback
import aiohttp
import aiomysql
from bs4 import BeautifulSoup
import discord
from discord.ext import commands
from PIL import Image

SERVICE_NAME = "UDC_Information"
TOKEN = os.getenv("TOKEN")
# クロール対象ページ
DENEN_URL = "https://supersolenoid.jp/blog-category-12.html"
DENEBLOG_URL = "https://deneblog.jp/blog-category-26.html"
# 入賞数ランキング
DISCORD_INFO_CHANNEL_ID = int(os.environ.get("DISCORD_INFO_CHANNEL_ID"))
# 新カード
DISCORD_NEWCARD_CHANNEL_ID = int(os.environ.get("DISCORD_NEWCARD_CHANNEL_ID"))
# CS結果
DISCORD_RESULT_CHANNEL_ID = int(os.environ.get("DISCORD_RESULT_CHANNEL_ID"))

# ログの設定
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
