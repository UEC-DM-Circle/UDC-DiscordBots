import asyncio
import datetime
import os
import random
import discord
from discord.ext import commands

TOKEN = os.getenv("TOKEN")
intent = discord.Intents.default()
intent.message_content = True

client = commands.Bot(command_prefix="?", intents=intent)

channel_id = int(os.getenv("CHANNEL_ID"))
test_id = int(os.getenv("TEST_ID"))
members = []
prev_match_list = []

# 0:待機中 1:試合中
mode = 0


async def matching():
    global members, prev_match_list
    match_list = []
    if len(members) > 2:
        members_copy = members.copy()
        while True:
            match_list = []
            random.shuffle(members_copy)
            if len(members_copy) % 2 == 1:
                kisu = True
            else:
                kisu = False
            for i in range(len(members_copy) // 2):
                match = members_copy[i] + " VS " + members_copy[i + 1]
                match_list.append(match)
            if kisu:
                match = members_copy[-1] + " is free."
                match_list.append(match)
            ok = True
            for match in match_list:
                if match in prev_match_list:
                    ok = False
                    break
            if ok:
                prev_match_list = match_list
                break
    elif len(members) == 2:
        match = members[0] + " VS " + members[1]
        match_list.append(match)
        prev_match_list = match_list
    return match_list


async def show_matching():
    channel = client.get_channel(channel_id)
    if channel == None:
        channel = client.get_channel(test_id)
    match_list = await matching()
    i = 1
    message = ""
    if match_list != []:
        for match in match_list:
            message += str(i) + ": " + match + "\n"
            i += 1
    else:
        message = "メンバーが少なすぎます。"
    await channel.send(message)


# ここを変更していく
@client.event
async def on_message(message):
    global mode, members
    if message.channel.id in [channel_id, test_id]:
        if message.content == "?test":
            await message.channel.send("Matching Bot is Working!")
        if message.content == "?start":
            if mode == 0:
                await message.channel.send("試合モードを開始します。")
                members.clear()
                mode = 1
        if mode == 1:
            if message.content == "?end":
                await message.channel.send("試合モードを終了します。")
                members.clear()
                mode = 0
            if message.content == "?join":
                members.append(message.author.name)
                await message.channel.send(message.author.name + "が参加しました。")
            if message.content == "?leave":
                if message.author.name in members:
                    members.remove(message.author.name)
                    await message.channel.send(message.author.name + "が退出しました。")
                else:
                    await message.channel.send("あなたは参加していません。")
            if message.content == "?show":
                members_list = ""
                for i in range(len(members)):
                    members_list += str(i + 1) + ": " + members[i] + "\n"
                if members_list == "":
                    members_list = "メンバーはいません。"
                await message.channel.send(members_list)
            if message.content.startswith("?add "):
                new = message.content[5:]
                if new not in members:
                    members.append(new)
                    await message.channel.send(new + "が参加しました。")
            if message.content == "?clear":
                members.clear()
                await message.channel.send("メンバーリストをクリアしました。")
            if message.content.startswith("?del "):
                number = message.content[5:]
                if number.isdigit():
                    number = int(number) - 1
                    if number < len(members):
                        members.pop(number)
                        await message.channel.send(
                            str(number + 1) + "番目のメンバーを削除しました。"
                        )
                    else:
                        await message.channel.send("その番号のメンバーは存在しません。")
            if message.content == "?match":
                await show_matching()


@client.event
async def on_ready():
    print("Bot is ready!")


client.run(TOKEN)
