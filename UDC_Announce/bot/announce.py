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


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


async def run_select_sql(sql: str):
    conn = get_connection()
    cursor = conn.cursor(buffered=True)
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result


@client.command()
async def test(ctx):
    if ctx.channel.id in (channel_id, test_channel_id):
        await ctx.send("Announcement Bot is Working!")


async def announce_tomorrow():
    channel = client.get_channel(channel_id)
    announcements = await run_select_sql(
        "SELECT title, place, comment FROM announcements WHERE date = CURDATE() AND is_today = 0"
    )
    if announcements:
        title, place, comment = announcements[0]
        text = f"@everyone\n\n明日は{title}です！\n場所：{place}"
        if comment:
            text += f"\n{comment}"
        await channel.send(text)


async def announce_today():
    channel = client.get_channel(channel_id)
    announcements = await run_select_sql(
        "SELECT title, place, comment FROM announcements WHERE date = CURDATE() AND is_today = 1"
    )
    if announcements:
        title, place, comment = announcements[0]
        text = f"@everyone\n\n今日は{title}です！\n場所：{place}"
        if comment:
            text += f"\n{comment}"
        await channel.send(text)


async def check_task():
    test_channel = client.get_channel(test_channel_id)
    announcements = await run_select_sql(
        "SELECT * FROM announcements WHERE date > CURDATE()"
    )
    if not announcements:
        await test_channel.send("日程を登録してください！")


async def check_time():
    while True:
        try:
            now = datetime.datetime.now()
            next_morning = now.replace(hour=6, minute=0, second=0, microsecond=0)
            if 6 <= now.hour < 18:
                pass
            else:
                if 18 <= now.hour <= 23:
                    next_morning += datetime.timedelta(days=1)
                seconds_until = (next_morning - now).total_seconds()
                wait_hours = int(seconds_until // 3600)
                seconds_until %= 3600
                await asyncio.sleep(seconds_until)
                for _ in range(wait_hours):
                    await check_task()
                    await asyncio.sleep(3600)
                await announce_today()
                await check_task()
            now = datetime.datetime.now()
            next_evening = now.replace(hour=18, minute=0, second=0, microsecond=0)
            seconds_until = (next_evening - now).total_seconds()
            wait_hours = int(seconds_until // 3600)
            seconds_until %= 3600
            await asyncio.sleep(seconds_until)
            for _ in range(wait_hours):
                await check_task()
                await asyncio.sleep(3600)
            await announce_tomorrow()
            await check_task()
        except Exception as e:
            print(f"Error: {e}")


@client.event
async def on_ready():
    print("Bot is ready!")
    await check_time()


client.run(TOKEN)
