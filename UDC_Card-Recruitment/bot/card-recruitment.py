import os
import discord
from discord.ext import commands
import mysql.connector
import asyncio

# 初期設定
TOKEN = os.getenv("TOKEN")
intent = discord.Intents.default()
intent.message_content = True
client = commands.Bot(command_prefix="-", intents=intent)
channel_id = int(os.environ.get("CHANNEL_ID"))
test_channel_id = int(os.environ.get("TEST_CHANNEL_ID"))


# MySQLの接続設定
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


async def run_sql(sql: str, params: tuple):
    conn = get_connection()
    cursor = conn.cursor(buffered=True)
    if params != ():
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    if sql.strip().upper().startswith("SELECT"):
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result
    else:
        conn.commit()
        cursor.close()
        conn.close()
        return


async def check_channel(ctx):
    if ctx.channel.id == channel_id or ctx.channel.id == test_channel_id:
        return True
    else:
        return False


async def check_ctx(ctx):
    if ctx.channel.id == channel_id or ctx.channel.id == test_channel_id:
        return True
    else:
        await ctx.send("このコマンドは指定されたチャンネルでのみ使用できます。")
        return False


@client.command()
async def test(ctx):
    if await check_channel(ctx):
        await ctx.send("Card-Recruitment Bot is Working!")


@client.command()
async def guide(ctx):
    if await check_channel(ctx):
        await ctx.send(
            "```"
            "【使い方を表示】\n"
            "-guide\n"
            "【募集追加】\n"
            "-want [カード名] [枚数]\n"
            "-want [人] [カード名] [枚数]\n"
            "※既存のカード名を指定した場合枚数が更新されます。\n"
            "　人を指定しない場合は自分の名前が使用されます。\n"
            "　半角スペースを含むカード名を入力しないようにしてください。\n"
            "【募集確認】\n"
            "-check [カード名/人](個別確認)\n"
            "-check (引数なしで全体確認)\n"
            "【募集終了】\n"
            "-end [カード名/募集ID]\n"
            "-end [人] [カード名/募集ID]\n"
            "```"
        )


@client.command()
async def want(ctx, *, args):
    args = args.split()
    if await check_channel(ctx):
        arg_length = len(args)
        if arg_length in [2, 3]:
            if arg_length == 2:
                person = ctx.author.display_name
                card = args[0]
                num = args[1]
            else:
                person = args[0]
                card = args[1]
                num = args[2]
            if num.isdecimal():
                num = int(num)
                recruitments = await run_sql(
                    "SELECT id, person, card, num, active FROM recruitments WHERE person = %s AND card = %s",
                    (person, card),
                )
                if recruitments != []:
                    id = recruitments[0][0]
                    current_num = recruitments[0][3]
                    active = recruitments[0][4]
                    if active == 1:
                        if current_num == num:
                            await ctx.send(
                                f"{person}さんは既にその内容の募集(ID: {id})を行っています。"
                            )
                            return
                        else:
                            await run_sql(
                                "UPDATE recruitments SET num = %s WHERE person = %s AND card = %s",
                                (num, person, card),
                            )
                            await ctx.send(
                                f"{person}さんの『{card}』の募集枚数を更新しました：\n×{current_num} → ×{num}"
                            )
                            return
                    else:
                        await run_sql(
                            "UPDATE recruitments SET active = 1, num = %s WHERE person = %s AND card = %s",
                            (num, person, card),
                        )
                        await ctx.send(
                            f"{person}さんの募集を受け付けました：\n{card} ×{num}"
                        )
                        return
                else:
                    # 新規追加
                    await run_sql(
                        "INSERT INTO recruitments (person, card, num) VALUES (%s, %s, %s)",
                        (person, card, num),
                    )
                    await ctx.send(
                        f"{person}さんの募集を受け付けました：\n{card} ×{num}"
                    )
                    return
        await ctx.send("募集追加方法に誤りがあります。")


@client.command()
async def check(ctx, *args):
    if await check_channel(ctx):
        recruitments = await run_sql(
            "SELECT id, person, card, num FROM recruitments WHERE active = 1",
            (),
        )
        if recruitments == []:
            await ctx.send("現在進行中の募集はありません。")
            return
        else:
            # 全募集を確認
            text = ""
            arg_length = len(args)
            if arg_length == 0:
                people = set()
                for recruitment in recruitments:
                    people.add(recruitment[1])
                for person in people:
                    buffa = []
                    for recruitment in recruitments:
                        if recruitment[1] == person:
                            buffa.append(
                                (recruitment[0], f"{recruitment[2]} ×{recruitment[3]}")
                            )
                    buffa = sorted(buffa, key=lambda x: x[0])
                    text += f"{person}さんの募集一覧\n"
                    for item in buffa:
                        text += f"・{item[0]}：{item[1]}\n"
                await ctx.send(text[:-1])
                return
            elif arg_length == 1:
                # 特定の人の募集を確認
                buffa = []
                person = args[0]
                for recruitment in recruitments:
                    if recruitment[1] == person:
                        buffa.append(
                            (recruitment[0], f"{recruitment[2]} ×{recruitment[3]}")
                        )
                if buffa != []:
                    buffa = sorted(buffa, key=lambda x: x[0])
                    text += f"{person}さんの募集一覧\n"
                    for item in buffa:
                        text += f"・{item[0]}：{item[1]}\n"
                    await ctx.send(text[:-1])
                    return
                # 特定のカードの募集を確認
                card = args[0]
                for recruitment in recruitments:
                    if recruitment[2] == card:
                        buffa.append(
                            (recruitment[0], f"×{recruitment[3]} by. {recruitment[1]}")
                        )
                if buffa != []:
                    buffa = sorted(buffa, key=lambda x: x[0])
                    text += f"『{card}』への募集一覧\n"
                    for item in buffa:
                        text += f"・{item[0]}：{item[1]}\n"
                    await ctx.send(text[:-1])
                    return
                await ctx.send("検索条件に該当する募集はありません。")
                return
            else:
                await ctx.send("募集確認方法に誤りがあります。")
                return


@client.command()
async def end(ctx, *, args):
    args = args.split()
    if await check_channel(ctx):
        arg_length = len(args)
        is_id = False
        if arg_length in [1, 2]:
            if arg_length == 1:
                name = ctx.author.display_name
                if args[0].isdecimal():
                    key = int(args[0])
                    is_id = True
                else:
                    key = args[0]
            else:
                name = args[0]
                if args[1].isdecimal():
                    key = int(args[1])
                    is_id = True
                else:
                    key = args[1]
            recruitments = await run_sql(
                "SELECT id FROM recruitments WHERE person = %s AND active = 1",
                (name,),
            )
            if recruitments == []:
                await ctx.send(f"{name}さんが募集しているカードはありません。")
                return
            if is_id:
                recruitment = await run_sql(
                    "SELECT id, card FROM recruitments WHERE person = %s AND id = %s",
                    (name, key),
                )
                if not recruitment:
                    await ctx.send(
                        f"{name}さんの募集の中に指定されたIDのものはありません。"
                    )
                    return
                card = recruitment[0][1]
                await run_sql(
                    "UPDATE recruitments SET active = 0, num = 0 WHERE id = %s",
                    (key,),
                )
                await ctx.send(
                    f"{name}さんが『{card}』 の募集(ID: {key})を終了しました。"
                )
            else:
                recruitment = await run_sql(
                    "SELECT id, card FROM recruitments WHERE person = %s AND card = %s",
                    (name, key),
                )
                if not recruitment:
                    await ctx.send(f"{name}さんは『{key}』の募集を行っていません。")
                    return
                await run_sql(
                    "UPDATE recruitments SET active = 0, num = 0 WHERE person = %s AND card = %s",
                    (name, key),
                )
                await ctx.send(f"{name}さんが『{key}』 の募集を終了しました。")
        else:
            await ctx.send("募集終了方法に誤りがあります。")
            return


client.run(TOKEN)
