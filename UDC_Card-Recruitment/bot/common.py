import os
import discord
from discord.ext import commands
import mysql.connector

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))
TEST_CHANNEL_ID = int(os.environ.get("TEST_CHANNEL_ID"))
