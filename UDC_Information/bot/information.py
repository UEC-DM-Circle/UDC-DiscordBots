from common import *
from use_mysql import UseMySQL
from crawler import Crawler
from logic import Logic

intent = discord.Intents.default()
intent.message_content = True
client = commands.Bot(command_prefix="+", intents=intent)
task = None


class Information:
    @staticmethod
    async def send_result_images(result_images: list, url: str, category: str):
        for result_image in result_images:
            if not await Logic.judge_isimage(result_image):
                continue
            sent = (
                await UseMySQL.run_sql(
                    "SELECT url FROM sent_images WHERE service = %s AND url = %s",
                    (SERVICE_NAME, result_image),
                )
                != []
            )
            if sent:
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
            sent = (
                await UseMySQL.run_sql(
                    "SELECT url FROM sent_images WHERE service = %s AND category = %s AND url = %s",
                    (SERVICE_NAME, category, new_info_image),
                )
                != []
            )
            if sent:
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
    async def send_message(channel_id: int, msg: str):
        await client.get_channel(channel_id).send(msg)


async def main():
    while True:
        try:
            # 田園補完計画→デネブログの順
            denen_new_articles = await Crawler.get_new_denen_articles()
            for denen_new_article in denen_new_articles:
                await Logic.decide_parser(denen_new_article)
            deneblog_new_articles = await Crawler.get_new_deneblog_articles()
            for deneblog_new_article in deneblog_new_articles:
                await Logic.decide_parser(deneblog_new_article)
        except Exception as e:
            print(f"Error: {e}")
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
    print("Bot is ready!")
    if task is None or task.done():
        task = asyncio.create_task(main())


client.run(TOKEN)
