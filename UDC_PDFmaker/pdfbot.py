import pdfgene as pg
import os
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
GENERATE = int(os.getenv("GENERATE"))
TEST=int(os.getenv("TEST"))

def is_making():
  if (os.path.isfile(pg.pdf_name)):
    print("is making!")
    return True
  if (os.path.isdir(pg.pics_folder_path)):
    print("is making!")
    return True
  print("isn't making!")
  return False

def legal_url(url: str):
  pattern = r'^https:\/\/gachi-matome\.com\/deckrecipe-detail-dm\/\?tcgrevo_deck_maker_deck_id=+'
  return bool(re.match(pattern, url))

#Bot定義
client = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@client.event
async def on_ready():
  print('ログインしました')

@client.command()
async def test(ctx):
  await ctx.send("test")

@client.command()
async def pdfmake(ctx, url: str):
  if ctx.channel.id not in [TEST,GENERATE]:
    await ctx.send("専用のチャンネルで実行してください")
    return
  if (not legal_url(url)):
    print("illegal")
    await ctx.send("urlが不正です")
    return
  if (is_making()):
    await ctx.send("時間をおいてもう一度お試しください")
    return
  await ctx.send("生成中です")
  pg.pdfgene(url=url)
  await ctx.send(file=discord.File(pg.pdf_name))
  await ctx.send(f"{ctx.author.mention} 生成完了しました")
  pg.rmpdf()


pg.rmpdf()

client.run(TOKEN)
