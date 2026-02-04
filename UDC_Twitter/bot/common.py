import datetime
import os
import asyncio
import traceback
import discord
from discord.ext import commands
import aiohttp
import aiomysql

SERVICE_NAME = "UDC_Twitter"
TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
TWITTER_USER_ID = os.getenv("TWITTER_USER_ID")
GET_TWEET_NUMBER = 5
