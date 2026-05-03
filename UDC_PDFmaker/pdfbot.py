from common import *
from pdfgene import generate_pdf_binary
from use_mysql import UseMySQL

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
    await write_log_message("ログインしました。", "INFO")


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
        await write_log_message("PDFの生成を開始...", "INFO")
        await ctx.send("PDFを生成中です。しばらくお待ちください。")
        pdf_binary = await generate_pdf_binary(url, ngr_option, nsp_option)
        # PDF生成に失敗
        if pdf_binary is None:
            raise PDFmakerError("PDFの生成に失敗しました。")
        await ctx.send(file=discord.File(fp=pdf_binary, filename=PDF_NAME))
        await ctx.send(f"{ctx.author.mention} PDFの生成が完了しました。")
    except PDFmakerError as e:
        await write_log_message(str(e), "ERROR")
        await ctx.send(str(e))
    except Exception as e:
        await write_log_message(str(e), "UNEXPECTED_ERROR")
        await ctx.send("予期せぬエラーが発生しました。管理者に連絡してください。")


client.run(TOKEN, log_handler=None)
