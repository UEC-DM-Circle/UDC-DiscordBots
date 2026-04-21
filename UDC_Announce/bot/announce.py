from common import *
from use_mysql import UseMySQL

intent = discord.Intents.default()
intent.message_content = True
client = commands.Bot(command_prefix="=", intents=intent)
task = None


class Announce:
    @staticmethod
    async def announce(is_today: bool):
        channel = client.get_channel(CHANNEL_ID)
        announcement = await UseMySQL.run_sql(
            "SELECT title, place, comment FROM announcements WHERE date = CURDATE() AND is_today = %s AND is_announced = 0",
            (is_today,),
        )
        if announcement:
            title, place, comment = announcement[0]
            date = "今日" if is_today else "明日"
            text = f"@everyone\n\n{date}は{title}です！\n場所：{place}"
            if comment:
                text += f"\n{comment}"
            await channel.send(text)
            await UseMySQL.run_sql(
                "UPDATE announcements SET is_announced = 1 WHERE date = CURDATE() AND is_today = %s",
                (is_today,),
            )

    @staticmethod
    async def check_task():
        test_channel = client.get_channel(TEST_CHANNEL_ID)
        next_announcement = await UseMySQL.run_sql(
            "SELECT * FROM announcements WHERE date > CURDATE()"
        )[0]
        if not next_announcement:
            await test_channel.send("日程を登録してください！")

    @classmethod
    async def check_time(cls):
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
                await cls.check_task()
                await asyncio.sleep(3600)
            await cls.announce(is_today=1)
            await cls.check_task()
        now = datetime.datetime.now()
        next_evening = now.replace(hour=18, minute=0, second=0, microsecond=0)
        seconds_until = (next_evening - now).total_seconds()
        wait_hours = int(seconds_until // 3600)
        seconds_until %= 3600
        await asyncio.sleep(seconds_until)
        for _ in range(wait_hours):
            await cls.check_task()
            await asyncio.sleep(3600)
        await cls.announce(is_today=0)
        await cls.check_task()

    @classmethod
    async def check_on_ready(cls):
        # 起動時にアナウンスできてないものがあればアナウンスする
        now = datetime.datetime.now()
        if 6 <= now.hour < 18:
            await cls.announce(is_today=1)
        elif 18 <= now.hour <= 23:
            await cls.announce(is_today=0)


async def main():
    await Announce.check_on_ready()
    while True:
        try:
            await Announce.check_time()
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()


async def check_channel(ctx) -> bool:
    return ctx.channel.id in (TEST_CHANNEL_ID, BOARD_MEMBER_CHANNEL_ID)


@client.command()
async def guide(ctx):
    if await check_channel(ctx):
        await ctx.send(
            "```"
            "【使い方を表示】\n"
            "=guide\n"
            "\n"
            "【Botの動作確認】\n"
            "=test\n"
            "\n"
            "【送信予定アナウンス一覧の確認】\n"
            "=check\n"
            "\n"
            "【新規アナウンスの追加】\n"
            "=add [タイトル] [日付] [場所] [時間] [コメント]\n"
            "※日付はYYYY-MM-DD形式で指定してください。\n"
            "　時間、コメントの指定は任意です。\n"
            "例: =add 定例会 2025-12-31 西2-106 16:00~21:00 大会あり\n"
            "\n"
            "【送信予定のキャンセル】\n"
            "=cancel [ID]\n"
            "指定したIDのアナウンスの送信予定をキャンセルします。\n"
            "```"
        )


@client.command()
async def test(ctx):
    if await check_channel(ctx):
        await ctx.send("Announce Bot is Working!")


@client.command()
async def check(ctx):
    if await check_channel(ctx):
        unsend_announcements = await UseMySQL.run_sql(
            "SELECT id, title, date, place, comment, is_today FROM announcements WHERE is_announced = 0 ORDER BY date ASC"
        )
        if unsend_announcements:
            message = "**送信予定アナウンス一覧**\n\n"
            for unsend_announcement in unsend_announcements:
                id, title, date, place, comment, is_today = unsend_announcement
                today_or_tomorrow = "当日告知" if is_today else "前日告知"
                message += f"ID：{id}\nタイトル：{title}\n日付：{date}({today_or_tomorrow})\n場所：{place}\n"
                if comment:
                    message += f"コメント：{comment}\n"
                message += "\n"
            message = message.strip()
            await ctx.send(message)
        else:
            await ctx.send("送信予定のアナウンスがありません。新規追加をお願いします。")


@client.command()
async def add(ctx, *args):
    if await check_channel(ctx):
        if len(args) < 3 or len(args) > 5:
            await ctx.send('不正な引数です。"=help"で使い方を確認してください。')
        title = args[0]
        date = args[1]
        try:
            date = datetime.datetime.strptime(args[1], "%Y-%m-%d").date()
        except ValueError:
            await ctx.send("日付はYYYY-MM-DD形式で指定してください。")
            return
        place = args[2]
        comment = ""
        if len(args) >= 4:
            comment = args[3]
        if len(args) >= 5:
            comment += ", " + args[4]
        if comment == "":
            await UseMySQL.run_sql(
                "INSERT INTO announcements (title, date, place, comment, is_today) VALUES (%s, %s, %s, NULL, 0)",
                (title, date - datetime.timedelta(days=1), place),
            )
            await UseMySQL.run_sql(
                "INSERT INTO announcements (title, date, place, comment, is_today) VALUES (%s, %s, %s, NULL, 1)",
                (title, date, place),
            )
        else:
            await UseMySQL.run_sql(
                "INSERT INTO announcements (title, date, place, comment, is_today) VALUES (%s, %s, %s, %s, 0)",
                (title, date - datetime.timedelta(days=1), place, comment),
            )
            await UseMySQL.run_sql(
                "INSERT INTO announcements (title, date, place, comment, is_today) VALUES (%s, %s, %s, %s, 1)",
                (title, date, place, comment),
            )
        await ctx.send("アナウンスを追加しました！")


@client.command()
async def cancel(ctx, *args):
    if await check_channel(ctx):
        if len(args) == 0:
            await ctx.send('引数が足りません。"=help"で使い方を確認してください。')
            return
        for arg in args:
            try:
                announcement_id = int(arg)
            except ValueError:
                await ctx.send("IDは整数で指定してください。")
                return
            result = await UseMySQL.run_sql(
                "UPDATE announcements SET is_announced = 1 WHERE id = %s AND is_announced = 0",
                (announcement_id,),
            )
            if result is None:
                await ctx.send(f"アナウンスの送信予定(ID: {arg})をキャンセルしました！")
            else:
                await ctx.send(
                    f"指定されたID({arg})のアナウンスが見つかりませんでした。"
                )


@client.event
async def on_ready():
    global task
    await UseMySQL.init_pool()
    print("Bot is ready!")
    if task is None or task.done():
        task = asyncio.create_task(main())


client.run(TOKEN)
