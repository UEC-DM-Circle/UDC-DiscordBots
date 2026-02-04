from common import *
from use_mysql import *

intent = discord.Intents.default()
intent.message_content = True
client = commands.Bot(command_prefix="~", intents=intent)
task = None


class Announce:
    @staticmethod
    async def announce_tomorrow():
        channel = client.get_channel(CHANNEL_ID)
        tomorrow_announcement = await UseMySQL.run_sql(
            "SELECT title, place, comment FROM announcements WHERE date = CURDATE() AND is_today = 0 AND is_announced = 0"
        )
        if tomorrow_announcement:
            title, place, comment = tomorrow_announcement
            text = f"@everyone\n\n明日は{title}です！\n場所：{place}"
            if comment:
                text += f"\n{comment}"
            await channel.send(text)
            await UseMySQL.run_sql(
                "UPDATE announcements SET is_announced = 1 WHERE date = CURDATE() AND is_today = 0"
            )

    @staticmethod
    async def announce_today():
        channel = client.get_channel(CHANNEL_ID)
        today_announcement = await UseMySQL.run_sql(
            "SELECT title, place, comment FROM announcements WHERE date = CURDATE() AND is_today = 1 AND is_announced = 0"
        )
        if today_announcement:
            title, place, comment = today_announcement
            text = f"@everyone\n\n今日は{title}です！\n場所：{place}"
            if comment:
                text += f"\n{comment}"
            await channel.send(text)
            await UseMySQL.run_sql(
                "UPDATE announcements SET is_announced = 1 WHERE date = CURDATE() AND is_today = 1"
            )

    @staticmethod
    async def check_task():
        test_channel = client.get_channel(TEST_CHANNEL_ID)
        next_announcement = await UseMySQL.run_sql(
            "SELECT * FROM announcements WHERE date > CURDATE()"
        )
        if not next_announcement:
            await test_channel.send("日程を登録してください！")

    @staticmethod
    async def check_time():
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
                await Announce.check_task()
                await asyncio.sleep(3600)
            await Announce.announce_today()
            await Announce.check_task()
        now = datetime.datetime.now()
        next_evening = now.replace(hour=18, minute=0, second=0, microsecond=0)
        seconds_until = (next_evening - now).total_seconds()
        wait_hours = int(seconds_until // 3600)
        seconds_until %= 3600
        await asyncio.sleep(seconds_until)
        for _ in range(wait_hours):
            await Announce.check_task()
            await asyncio.sleep(3600)
        await Announce.announce_tomorrow()
        await Announce.check_task()

    @staticmethod
    async def check_on_ready():
        # 起動時にアナウンスできてないものがあればアナウンスする
        now = datetime.datetime.now()
        if 6 <= now.hour < 18:
            await Announce.announce_today()
        else:
            await Announce.announce_tomorrow()


async def main():
    await Announce.check_on_ready()
    while True:
        try:
            await Announce.check_time()
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()


@client.command()
async def test(ctx):
    if ctx.channel.id in (CHANNEL_ID, TEST_CHANNEL_ID):
        await ctx.send("Announcement Bot is Working!")


@client.event
async def on_ready():
    global task
    await UseMySQL.init_pool()
    print("Bot is ready!")
    if task is None or task.done():
        task = asyncio.create_task(main())


client.run(TOKEN)
