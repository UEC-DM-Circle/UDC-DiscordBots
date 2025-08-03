import discord
from discord.ext import commands
import mysql.connector
import os
import datetime
import asyncio

TOKEN = os.getenv("TOKEN")
intent = discord.Intents.default()
intent.message_content = True

client = commands.Bot(command_prefix="~", intents=intent)

channel_id = int(os.environ.get("CHANNEL_ID"))
test_channel_id = int(os.environ.get("TEST_CHANNEL_ID"))

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    username=os.getenv("DB_USERNAME"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
)
cursor = conn.cursor(buffered=True)


@client.command()
async def test(ctx):
    if ctx.channel.id == channel_id or ctx.channel.id == test_channel_id:
        await ctx.send("Announcement Bot is Working!")
    return


async def announce_tomorrow():
    channel = client.get_channel(channel_id)
    cursor.execute(
        "SELECT title, place, comment FROM tasks WHERE date = CURDATE() AND is_today = 0"
    )
    tasks = cursor.fetchall()
    if tasks != []:
        title = tasks[0][1]
        place = tasks[0][2]
        comment = tasks[0][3]
        text = f"@everyone\n\n明日は{title}です！\n場所：{place}"
        if comment:
            text += f"\n{comment}"
        await channel.send(text)
    return


async def announce_today():
    channel = client.get_channel(channel_id)
    cursor.execute(
        "SELECT title, place, comment FROM tasks WHERE date = CURDATE() AND is_today = 1"
    )
    tasks = cursor.fetchall()
    if tasks != []:
        title = tasks[0][1]
        place = tasks[0][2]
        comment = tasks[0][3]
        text = f"@everyone\n\n今日は{title}です！\n場所：{place}"
        if comment:
            text += f"\n{comment}"
        await channel.send(text)
    return


async def check_task():
    test_channel = client.get_channel(test_channel_id)
    cursor.execute("SELECT * FROM tasks WHERE date > CURDATE()")
    tasks = cursor.fetchall()
    if tasks == []:
        await test_channel.send("日程を登録してください！")
    return


async def check_time():
    while True:
        now = datetime.datetime.now()
        next_morning = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if 6 <= now.hour < 18:
            pass
        else:
            if 18 <= now.hour <= 23:
                next_morning += datetime.timedelta(days=1)
            seconds_until = (next_morning - now).total_seconds()
            await asyncio.sleep(seconds_until)
            await announce_today()
            await check_task()
        now = datetime.datetime.now()
        next_evening = now.replace(hour=18, minute=0, second=0, microsecond=0)
        seconds_until = (next_evening - now).total_seconds()
        await asyncio.sleep(seconds_until)
        await announce_tomorrow()
        await check_task()


@client.event
async def on_ready():
    print("Bot is ready!")
    await check_time()


client.run(TOKEN)
