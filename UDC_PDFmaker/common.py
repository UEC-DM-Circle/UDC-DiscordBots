import asyncio
from io import BytesIO
import logging
import logging.handlers
import os
import re
import time
import cv2
import discord
from discord.ext import commands
from dotenv import load_dotenv
import numpy as np
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.utils import ImageReader
import requests
from urllib.parse import urlparse, parse_qs
from exception import PDFmakerError

load_dotenv()
TOKEN = os.getenv("TOKEN")
GENERATE_CHANNEL_ID = int(os.getenv("GENERATE_CHANNEL_ID"))
TEST_CHANNEL_ID = int(os.getenv("TEST_CHANNEL_ID"))
API_BASE_URL = os.getenv("API_BASE_URL")
IMAGE_BASE_URL = os.getenv("IMAGE_BASE_URL")
PDF_NAME = "artifact.pdf"
SERVICE_NAME = "UDC_PDFmaker"
# ログの設定
LOG_FILE_NAME = "udc_pdfmaker.log"
handler = logging.handlers.RotatingFileHandler(
    filename=LOG_FILE_NAME,
    encoding="utf-8",
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
)
discord.utils.setup_logging(level=logging.INFO, handler=handler)
bot_logger = logging.getLogger("PDFmaker")


async def write_log_message(message: str, category: str):
    if category == "INFO":
        bot_logger.info(message)
    elif category == "ERROR":
        bot_logger.error(message)
    else:
        bot_logger.warning(message)
