from common import *
from crawler import Crawler
from logic import Logic
from parser import Parser
from use_mysql import UseMySQL

intent = discord.Intents.default()
intent.message_content = True
client = commands.Bot(command_prefix="+", intents=intent)
task = None


class Information:
    # 各々切り分けてね
    # 画像が送信済みかの判定：重いので直近1カ月以内のものに重複があるかをチェック
    @staticmethod
    async def decide_process_method(new_article: dict):
        url = new_article["url"]
        title = new_article["title"]
        category = new_article["category"]
        match category:
            case "ranking":
                ranking_img = await Parser.parse_ranking(new_article)
                if not ranking_img:
                    return
                await Information.send_message(DISCORD_INFO_CHANNEL_ID, ranking_img)
            case "many_cs_results":
                many_cs_results = await Parser.parse_many_cs_results(new_article)
                if not many_cs_results:
                    return
                for cs_result in many_cs_results:
                    await Information.send_message(
                        DISCORD_RESULT_CHANNEL_ID, cs_result["result_sentence"]
                    )
                    for tweet_url, tweet_text in zip(
                        cs_result["result_tweets"], cs_result["tweet_texts"]
                    ):
                        tweet_id = tweet_url.split("/")[-1]
                        await UseMySQL.run_sql(
                            "INSERT INTO tweets (text, tweet_id, url) VALUES (%s, %s, %s)",
                            (
                                tweet_text,
                                tweet_id,
                                tweet_url,
                            ),
                        )
                        await Information.send_message(
                            DISCORD_RESULT_CHANNEL_ID, tweet_url
                        )
                await UseMySQL.run_sql(
                    "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
                    (url, title, category, SERVICE_NAME),
                )
            case "hatti_cs_result":
                message, result_images = await Parser.parse_hatti_cs_result(new_article)
                if not message or not result_images:
                    return
                await UseMySQL.run_sql(
                    "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
                    (url, title, category, SERVICE_NAME),
                )
                await Information.send_message(DISCORD_RESULT_CHANNEL_ID, message)
                await Information.send_result_images(result_images, url, category)
            case "ryusei_cs_result":
                message, result_images = await Parser.parse_ryusei_cs_result(
                    new_article
                )
                if not message or not result_images:
                    return
                await UseMySQL.run_sql(
                    "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
                    (url, title, category, SERVICE_NAME),
                )
                await Information.send_message(DISCORD_RESULT_CHANNEL_ID, message)
                await Information.send_result_images(result_images, url, category)
            case "gp_result":
                message, result_images = await Parser.parse_gp_result(new_article)
                if not message or not result_images:
                    return
                # 結果の送信とDBへの登録は初回のみ
                if not await Logic.judge_iscrawled(url, category):
                    await Information.send_message(DISCORD_RESULT_CHANNEL_ID, message)
                    await UseMySQL.run_sql(
                        "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
                        (url, title, category, SERVICE_NAME),
                    )
                # 後から画像が追加されることもある
                await Information.send_result_images(result_images, url, category)
            case "cs_result":
                message, result_images = await Parser.parse_cs_result(new_article)
                if not message or not result_images:
                    return
                await UseMySQL.run_sql(
                    "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
                    (url, title, category, SERVICE_NAME),
                )
                await Information.send_message(DISCORD_RESULT_CHANNEL_ID, message)
                await Information.send_result_images(result_images, url, category)
            case "gold_treasure":
                newcard_images = await Parser.parse_gold_treasure(new_article)
                if not newcard_images:
                    return
                await Information.send_new_info_images(newcard_images, url, category)
            case "new_card":
                newcard_images = await Parser.parse_new_card(new_article)
                if not newcard_images:
                    return
                await UseMySQL.run_sql(
                    "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
                    (
                        url,
                        title,
                        category,
                        SERVICE_NAME,
                    ),
                )
                await Information.send_new_info_images(newcard_images, url, category)
            case "stream":
                streamed_images = await Parser.parse_stream(new_article)
                if streamed_images == []:
                    return
                await Information.send_new_info_images(streamed_images, url, category)
                return
            case "etc":
                pass

    @staticmethod
    async def send_result_images(result_images: list, url: str, category: str):
        for result_image in result_images:
            if not await Logic.judge_isimage(result_image):
                continue
            if await Logic.judge_issent(result_image, category):
                continue
            deck_image_size = await Crawler.try_to_get_image_size(result_image)
            await Crawler.register_crawl(result_image, "HTTP_GET")
            await UseMySQL.run_sql(
                "INSERT INTO sent_images (url, original_url, category, service, width, height) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    result_image,
                    url,
                    category,
                    SERVICE_NAME,
                    deck_image_size[0],
                    deck_image_size[1],
                ),
            )
            await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(result_image)
        return

    @staticmethod
    async def send_new_info_images(new_info_images: list, url: str, category: str):
        for new_info_image in new_info_images:
            if not await Logic.judge_isimage(new_info_image):
                continue
            if await Logic.judge_issent(new_info_image, category):
                continue
            newcard_image_size = await Crawler.try_to_get_image_size(new_info_image)
            if (
                newcard_image_size[0] == newcard_image_size[1]
                and newcard_image_size[0] != 0
            ):
                # 正方形画像は広告
                continue
            await Crawler.register_crawl(new_info_image, "HTTP_GET")
            await UseMySQL.run_sql(
                "INSERT INTO sent_images (url, original_url, category, service, width, height) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    new_info_image,
                    url,
                    category,
                    SERVICE_NAME,
                    newcard_image_size[0],
                    newcard_image_size[1],
                ),
            )
            await client.get_channel(DISCORD_NEWCARD_CHANNEL_ID).send(new_info_image)
        return

    @staticmethod
    async def send_message(channel_id: int, message: str):
        message = message.replace("\n\n\n", "\n\n")
        await client.get_channel(channel_id).send(message)


async def main():
    while True:
        try:
            # 田園補完計画→デネブログの順
            denen_new_articles = await Crawler.get_new_denen_articles()
            for denen_new_article in denen_new_articles:
                await Information.decide_process_method(denen_new_article)
            deneblog_new_articles = await Crawler.get_new_deneblog_articles()
            for deneblog_new_article in deneblog_new_articles:
                await Information.decide_process_method(deneblog_new_article)
        except Exception as e:
            await write_log_message(f"{e}", "ERROR")
            traceback.print_exc()
        await asyncio.sleep(60)


@client.command()
async def test(ctx):
    if ctx.channel.id == DISCORD_INFO_CHANNEL_ID:
        await ctx.send("Information bot is working!")


@client.event
async def on_ready():
    global task
    await Crawler.init_session()
    await UseMySQL.init_pool()
    await write_log_message("Bot is ready!", "INFO")
    if task is None or task.done():
        task = asyncio.create_task(main())


client.run(TOKEN, log_handler=None)
