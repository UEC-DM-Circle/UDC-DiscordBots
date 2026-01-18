import asyncio
import datetime
import os
import traceback
import discord
from discord.ext import commands
import aiomysql

TOKEN = os.getenv("TOKEN")
channel_id = int(os.environ.get("CHANNEL_ID"))
test_channel_id = int(os.environ.get("TEST_CHANNEL_ID"))
intent = discord.Intents.default()
intent.message_content = True
client = commands.Bot(command_prefix="~", intents=intent)
task = None


class UseMySQL:
    pool: aiomysql.Pool | None = None

    @classmethod
    async def init_pool(cls):
        if cls.pool is None:
            cls.pool = await aiomysql.create_pool(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                db=os.getenv("DB_NAME"),
                autocommit=True,
                minsize=1,
                maxsize=5,
            )

    @classmethod
    async def close_pool(cls):
        if cls.pool:
            cls.pool.close()
            await cls.pool.wait_closed()
            cls.pool = None

    @classmethod
    async def run_sql(cls, sql: str, params: tuple = ()) -> list | None:
        async with cls.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                if sql.strip().upper().startswith("SELECT"):
                    rows = await cur.fetchall()
                    print([r[0] if isinstance(r, tuple) else r for r in rows])
                    return rows[0] if rows else None


class Announce:
    @staticmethod
    async def announce_tomorrow():
        channel = client.get_channel(channel_id)
        announcements = await UseMySQL.run_sql(
            "SELECT title, place, comment FROM announcements WHERE date = CURDATE() AND is_today = 0 AND is_announced = 0"
        )
        if announcements:
            title, place, comment = announcements
            text = f"@everyone\n\n明日は{title}です！\n場所：{place}"
            if comment:
                text += f"\n{comment}"
            await channel.send(text)
            await UseMySQL.run_sql(
                "UPDATE announcements SET is_announced = 1 WHERE date = CURDATE() AND is_today = 0"
            )

    @staticmethod
    async def announce_today():
        channel = client.get_channel(channel_id)
        announcements = await UseMySQL.run_sql(
            "SELECT title, place, comment FROM announcements WHERE date = CURDATE() AND is_today = 1 AND is_announced = 0"
        )
        if not announcements:
            title, place, comment = announcements
            text = f"@everyone\n\n今日は{title}です！\n場所：{place}"
            if comment:
                text += f"\n{comment}"
            await channel.send(text)
            await UseMySQL.run_sql(
                "UPDATE announcements SET is_announced = 1 WHERE date = CURDATE() AND is_today = 1"
            )

    @staticmethod
    async def check_task():
        test_channel = client.get_channel(test_channel_id)
        announcements = await UseMySQL.run_sql(
            "SELECT * FROM announcements WHERE date > CURDATE()"
        )
        if not announcements:
            await test_channel.send("日程を登録してください！")

    @staticmethod
    async def check_time():
        now = datetime.datetime.now()
        if now.hour == 6:
            await Announce.announce_today()
        elif now.hour == 18:
            await Announce.announce_tomorrow()
        await Announce.check_task()


async def main():
    while True:
        try:
            await Announce.check_time()
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
        await asyncio.sleep(3600)


@client.command()
async def test(ctx):
    if ctx.channel.id in (channel_id, test_channel_id):
        await ctx.send("Announcement Bot is Working!")


@client.event
async def on_ready():
    global task
    await UseMySQL.init_pool()
    print("Bot is ready!")
    if task is None or task.done():
        task = asyncio.create_task(main())


client.run(TOKEN)
