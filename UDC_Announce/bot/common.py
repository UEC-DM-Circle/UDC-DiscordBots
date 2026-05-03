import asyncio
import datetime
import os
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
