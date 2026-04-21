import asyncio
import datetime
import os
import traceback
import discord
from discord.ext import commands
import aiomysql

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))
TEST_CHANNEL_ID = int(os.environ.get("TEST_CHANNEL_ID"))
BOARD_MEMBER_CHANNEL_ID = int(os.environ.get("BOARD_MEMBER_CHANNEL_ID"))
