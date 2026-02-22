import os
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
GENERATE_CHANNEL_ID = int(os.getenv("GENERATE_CHANNEL_ID"))
TEST_CHANNEL_ID = int(os.getenv("TEST_CHANNEL_ID"))
PDF_NAME = "artifact.pdf"
