import os
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv
from exception import PDFmakerError
from pdfgene import generate_pdf_binary
from use_mysql import UseMySQL

load_dotenv()
TOKEN = os.getenv("TOKEN")
GENERATE_CHANNEL_ID = int(os.getenv("GENERATE_CHANNEL_ID"))
TEST_CHANNEL_ID = int(os.getenv("TEST_CHANNEL_ID"))
PDF_NAME = "artifact.pdf"
# Bot定義
client = commands.Bot(command_prefix="!", intents=discord.Intents.all())


def legal_url(url: str) -> bool:
    pattern = r"^https:\/\/gachi-matome\.com\/deckrecipe-detail-dm\/\?tcgrevo_deck_maker_deck_id=+"
    return bool(re.match(pattern, url))


def register_to_database(user: str, option: str, url: str):
    UseMySQL.run_sql(
        "INSERT INTO pdf_requests (user, options, url) VALUES (%s, %s, %s)",
        (user, option, url),
    )


@client.event
async def on_ready():
    print("INFO: ログインしました。")


@client.command()
async def test(ctx):
    await ctx.send("test")


@client.command()
async def pdfmake(ctx, *args):
    try:
        if ctx.channel.id not in [TEST_CHANNEL_ID, GENERATE_CHANNEL_ID]:
            raise PDFmakerError("専用のチャンネルで実行してください。")
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
        register_to_database(
            ctx.author.display_name, f"-ngr={ngr_option} -nsp={nsp_option}", url
        )
        if not legal_url(url):
            raise PDFmakerError("指定されたURLが不正です。")
        print("INFO: Starting PDF generation...")
        await ctx.send("PDFの生成中です。しばらくお待ちください。")
        pdf_binary = generate_pdf_binary(url, ngr_option, nsp_option)
        # PDF生成に失敗
        if pdf_binary is None:
            raise PDFmakerError("PDFの生成に失敗しました。")
        await ctx.send(file=discord.File(fp=pdf_binary, filename=PDF_NAME))
        await ctx.send(f"{ctx.author.mention} PDFの生成が完了しました。")
    except PDFmakerError as e:
        print(f"ERROR: {str(e)}")
        await ctx.send(str(e))
    except Exception as e:
        print(f"UNEXPECTED ERROR: {str(e)}")
        await ctx.send("予期せぬエラーが発生しました。管理者に連絡してください。")


client.run(TOKEN)
