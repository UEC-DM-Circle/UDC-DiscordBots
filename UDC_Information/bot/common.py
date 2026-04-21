import io
import os
import asyncio
import socket
import traceback
import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import aiomysql
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
