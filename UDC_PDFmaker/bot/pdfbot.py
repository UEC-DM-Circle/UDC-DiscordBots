from pdfgene import generate_pdf_binary
import os
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
GENERATE = int(os.getenv("GENERATE"))
TEST=int(os.getenv("TEST"))
pdf_name = "artifact.pdf"

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
async def pdfmake(ctx, *args):
  if ctx.channel.id not in [TEST,GENERATE]:
    await ctx.send("専用のチャンネルで実行してください")
    return
  url = None
  ngr_option = False
  nsp_option = False
  for arg in args:
    if arg == "-ngr":
      ngr_option = True
    elif arg == "-nsp":
      nsp_option = True
    elif arg.startswith("http"):
      url = arg

  if (not legal_url(url)):
    print("illegal")
    await ctx.send("urlが不正です")
    return

  await ctx.send("生成中です")
  pdf_binary = generate_pdf_binary(url, ngr_option, nsp_option)
  await ctx.send(file=discord.File(fp=pdf_binary, filename=pdf_name))
  await ctx.send(f"{ctx.author.mention} 生成完了しました")


client.run(TOKEN)
