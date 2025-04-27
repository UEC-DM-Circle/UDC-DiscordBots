import os
import json
import asyncio
import discord
from discord.ext import commands
from save_list import *

# 初期設定
TOKEN = os.getenv("TOKEN")
intent = discord.Intents.default()
intent.message_content= True
client = commands.Bot(
    command_prefix='-',
    intents=intent
)
channel_id = int(os.environ.get("CHANNEL_ID"))
test_channel_id = int(os.environ.get("TEST_CHANNEL_ID"))
log_channel_id = int(os.environ.get("LOG_CHANNEL_ID"))

async def check_channel(ctx):
    if ctx.channel.id == channel_id or ctx.channel.id == test_channel_id:
        return True
    else:
        return False

# コマンド
@client.command()
async def guide(ctx):
    if await check_channel(ctx):
        await ctx.send(
            "```"
            "【使い方を表示】\n"
            "-guide\n"
            "【募集追加】\n"
            "-want [カード名] [枚数]\n"
            "※既存のカード名を指定した場合枚数が更新されます。\n"
            "【募集確認】\n"
            "-check [カード名/人](個別確認)\n"
            "-check (引数なしで全体確認)\n"
            "【募集終了】\n"
            "-end [カード名]\n"
            "```"
        )
@client.command()
async def want(ctx, *args):
    if await check_channel(ctx):
        foo = len(args)
        if foo in [2, 3]:
            if foo == 2:
                person = ctx.author.display_name
                want = args[0]
                num = args[1]
            else:
                person = args[0]
                want = args[1]
                num = args[2]
            if num.isdecimal():
                num = int(num)
                if person in recruitment:
                    for i in range(len(recruitment[person])):
                        if recruitment[person][i]["want"] == want:
                            buf = recruitment[person][i]["num"]
                            recruitment[person][i]["num"] = num
                            state = recruitment[person][i]["active"]
                            recruitment[person][i]["active"] = True
                            if state:
                                if buf != num:
                                    await ctx.send(f"{person}さんの募集を更新しました：\n{want} ×{buf} → ×{num}")
                                else:
                                    await ctx.send(f"{person}さんはすでにその内容の募集を行っています。")
                            else:
                                ctx.send(f"{person}さんの募集を受け付けました：\n{want} ×{num}")
                            return
                    recruitment[person].append({"want":want, "num":num, "active":True})
                else:
                    recruitment[person] = [{"want":want, "num":num, "active":True}]
                await ctx.send(f"{person}さんの募集を受け付けました：\n{want} ×{num}")
                return
        await ctx.send("募集追加方法に誤りがあります。")
@client.command()
async def check(ctx, *args):
    text=""
    if await check_channel(ctx):
        active_recruitment_number = 0
        for key in recruitment:
            for i in range(len(recruitment[key])):
                if recruitment[key][i]["active"]:
                    active_recruitment_number += 1
        if active_recruitment_number == 0:
            text = "現在進行中の募集はありません。\n"
        else:
            if len(args) == 0:
                buffa={}
                for key in recruitment:
                    for i in range(len(recruitment[key])):
                        if recruitment[key][i]["active"]:
                            if key in buffa:
                                buffa[key].append([recruitment[key][i]["want"], recruitment[key][i]["num"]])
                            else:
                                buffa[key] = [[recruitment[key][i]["want"], recruitment[key][i]["num"]]]
                for key in buffa:
                    text += f"{key}さんの募集一覧\n"
                    for i in range(len(buffa[key])):
                        text += f"・{buffa[key][i][0]} ×{buffa[key][i][1]}\n"
            elif len(args) == 1:
                buffa={}
                for key in recruitment:
                    if key == args[0]:
                        for i in range(len(recruitment[key])):
                            if recruitment[key][i]["active"]:
                                if key in buffa:
                                    buffa[key].append([recruitment[key][i]["want"], recruitment[key][i]["num"]])
                                else:
                                    buffa[key] = [[recruitment[key][i]["want"], recruitment[key][i]["num"]]]
                if buffa=={}:
                    for key in recruitment:
                        for i in range(len(recruitment[key])):
                            if recruitment[key][i]["want"] == args[0]:
                                if recruitment[key][i]["active"]:
                                    foo = recruitment[key][i]["want"]
                                    if foo in buffa:
                                        buffa[foo].append([key, recruitment[key][i]["num"]])
                                    else:
                                        buffa[foo] = [[key, recruitment[key][i]["num"]]]
                    for key in buffa:
                        text += f"「{key}」への募集一覧\n"
                        for i in range(len(buffa[key])):
                            text += f"・{buffa[key][i][0]}：{buffa[key][i][1]}枚\n"
                else:
                    for key in buffa:
                        text += f"{key}さんの募集一覧\n"
                        for i in range(len(buffa[key])):
                            text += f"・{buffa[key][i][0]} ×{buffa[key][i][1]}\n"
                if buffa=={}:
                    text = "該当する募集がありません。\n"
            else:
                text += "募集確認方法に誤りがあります。\n"
        text = text[:-1]
        await ctx.send(text)
@client.command()
async def end(ctx, *args):
    if await check_channel(ctx):
        foo = len(args)
        if foo in [1,2]:
            if foo == 1:
                bar = ctx.author.display_name
                card = args[0]
            else:
                bar = args[0]
                card = args[1]
            if bar in recruitment:
                argument = recruitment[bar]
                flag = True
                for wanted in argument:
                    if wanted["want"] == card:
                        wanted["active"] = False
                        wanted["num"] = 0
                        flag = False
                if flag:
                    await ctx.send(f"{bar}さんは「{card}」 を募集していません。")
                else:
                    await ctx.send(f"{bar}さんが「{card}」 の募集を終了しました。")
            else:
                await ctx.send(f"{bar}さんが募集しているカードはありません。")
        else:
            await ctx.send("募集終了方法に誤りがあります。")
@client.command()
async def test(ctx):
    if await check_channel(ctx):
        await ctx.send("Card-Recruitment Bot is Working!")
async def send_log():
    global recruitment
    channel = client.get_channel(log_channel_id)
    buffa = {
        key: [
            {'want': item["want"], 'num': item["num"], 'active': True}
            for item in recruitment[key] if item["active"]
        ]
        for key in recruitment if any(item["active"] for item in recruitment[key])
    }
    recruitment = buffa
    with open("recruitment.json", "w", encoding="utf-8") as file:
        json.dump(recruitment, file, ensure_ascii=False)
    await channel.send(file = discord.File("recruitment.json"))
    os.remove("recruitment.json")
@client.event
async def on_ready():
    await send_log()
    channel = client.get_channel(log_channel_id)
    print("Bot is ready!")
    while True:
        await asyncio.sleep(900)
        await send_log()

client.run(TOKEN)