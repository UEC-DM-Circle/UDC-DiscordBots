import io
import os
import asyncio
import traceback
import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
import aiomysql
from PIL import Image

SERVICE_NAME = "UDC_Information"
TOKEN = os.getenv("TOKEN")
# クロール対象ページ
TARGET_URL = "https://supersolenoid.jp/blog-category-12.html"
# 入賞数ランキング
DISCORD_INFO_CHANNEL_ID = int(os.environ.get("DISCORD_INFO_CHANNEL_ID"))
# 新カード
DISCORD_NEWCARD_CHANNEL_ID = int(os.environ.get("DISCORD_NEWCARD_CHANNEL_ID"))
# CS結果
DISCORD_RESULT_CHANNEL_ID = int(os.environ.get("DISCORD_RESULT_CHANNEL_ID"))
intent = discord.Intents.default()
intent.message_content = True
client = commands.Bot(command_prefix="+", intents=intent)
task = None


class UseMySQL:
    pool: aiomysql.Pool | None = None

    @classmethod
    async def init_pool(cls):
        if cls.pool is None:
            cls.pool = await aiomysql.create_pool(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                db=os.getenv("DB_NAME"),
                autocommit=True,
                minsize=1,
                maxsize=5,
            )

    @classmethod
    async def close_pool(cls):
        if cls.pool:
            cls.pool.close()
            await cls.pool.wait_closed()
            cls.pool = None

    @classmethod
    async def run_sql(cls, sql: str, params: tuple = ()) -> list | None:
        async with cls.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                if sql.strip().upper().startswith("SELECT"):
                    rows = await cur.fetchall()
                    return [r[0] if isinstance(r, tuple) else r for r in rows]


class Logic:

    @staticmethod
    async def judge_category(title: str) -> str:
        if "入賞数ランキング" in title:
            return "ranking"
        if "結果" in title:
            if "など大会結果" in title:
                # https://supersolenoid.jp/blog-entry-42601.html
                return "many_cs_results"
            if any(x in title for x in ("はっちCS", "はっちcs")):
                # https://supersolenoid.jp/blog-entry-42779.html
                # https://supersolenoid.jp/blog-entry-42860.html
                # https://supersolenoid.jp/blog-entry-42944.html
                return "hatti_cs_result"
            if "DMGP" in title:
                # https://supersolenoid.jp/blog-entry-42560.html
                return "gp_result"
            # https://supersolenoid.jp/blog-entry-42770.html
            return "cs_result"
        if any(x in title for x in ("が公開", "多数公開", "が判明", "が全種公開", "プレミア公開")):
            # https://supersolenoid.jp/blog-entry-42669.html
            if "よくある質問" not in title:
                return "new_card"
        if "新情報まとめ" in title:
            # https://supersolenoid.jp/blog-entry-42757.html
            return "stream"
        return "etc"

    @staticmethod
    async def decide_parser(new_article: dict):
        match new_article["category"]:
            case "ranking":
                await Parser.parse_ranking(new_article)
            case "many_cs_results":
                await Parser.parse_many_cs_results(new_article)
            case "hatti_cs_result":
                await Parser.parse_hatti_cs_result(new_article)
            case "gp_result":
                await Parser.parse_gp_result(new_article)
            case "cs_result":
                await Parser.parse_cs_result(new_article)
            case "new_card":
                await Parser.parse_new_card(new_article)
            case "stream":
                await Parser.parse_stream(new_article)
            case "etc":
                pass

    # send_result_imagesとsend_new_info_imagesを統合する
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
                    "SELECT url FROM sent_images WHERE service = %s AND (category = 'new_card' OR category = 'stream') AND url = %s",
                    (SERVICE_NAME, new_info_image),
                )
                != []
            )
            if sent:
                continue
            newcard_image_size = await Crawler.try_to_get_image_size(new_info_image)
            # if category == "stream":
            #     if newcard_image_size[0] >= 1500:
            #         # 横長画像は広告
            #         continue
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

    # 上に持ってくる
    @staticmethod
    async def judge_isimage(url: str) -> bool:
        return url.startswith("https") and any(
            ext in url for ext in (".jpg", ".jpeg", ".png", ".gif")
        )


class Crawler:
    session: aiohttp.ClientSession | None = None

    @classmethod
    async def init_session(cls):
        if cls.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            cls.session = aiohttp.ClientSession(timeout=timeout)

    @classmethod
    async def close_session(cls):
        if cls.session:
            await cls.session.close()
            cls.session = None

    @classmethod
    async def get_image_size(cls, url: str) -> tuple:
        try:
            await asyncio.sleep(1)
            async with cls.session.get(url) as resp:
                if resp.status != 200:
                    return "ERROR"
                data = await resp.read()
                image = Image.open(io.BytesIO(data))
                image.verify()
                return image.size
        except Exception:
            return "ERROR"

    @classmethod
    async def try_to_get_image_size(cls, url: str, retries: int = 5) -> tuple:
        for _ in range(retries):
            size = await cls.get_image_size(url)
            if size != "ERROR":
                return size
        return (0, 0)  # サイズが見つからない場合は(0, 0)を返す

    @classmethod
    async def get_soup(cls, url: str) -> BeautifulSoup | str:
        try:
            await asyncio.sleep(1)
            async with cls.session.get(url) as resp:
                if resp.status != 200:
                    return "ERROR"
                text = await resp.text()
                return BeautifulSoup(text, "html.parser")
        except Exception:
            return "ERROR"

    @classmethod
    async def try_to_get_soup(cls, url: str, retries: int = 5) -> BeautifulSoup | str:
        for _ in range(retries):
            soup = await cls.get_soup(url)
            if soup != "ERROR":
                return soup
        return "FAILED"

    @staticmethod
    async def register_crawl(target_url: str, method: str):
        await UseMySQL.run_sql(
            "INSERT INTO crawls (target_url, method, service) VALUES (%s, %s, %s)",
            (target_url, method, SERVICE_NAME),
        )

    @classmethod
    async def get_new_articles(cls) -> list:
        soup = await cls.try_to_get_soup(TARGET_URL)
        if soup == "FAILED":
            return []
        await cls.register_crawl(TARGET_URL, "HTTP_GET")
        titles = soup.find_all("div", class_="EntryTitle")
        new_articles = []
        for div in titles:
            a = div.find("a")
            if not a:
                continue
            url = a.get("href")
            title = div.text
            category = await Logic.judge_category(title)
            new_articles.append({"url": url, "title": title, "category": category})
        return new_articles


class Parser:
    # 全体的に共通部分をまとめる
    @staticmethod
    async def parse_ranking(new_article: dict):
        sent_urls = await UseMySQL.run_sql(
            "SELECT url FROM sent_urls WHERE service = %s AND category = 'ranking'",
            (SERVICE_NAME,),
        )
        url = new_article["url"]
        # パースは一回でOK
        if url in sent_urls:
            return
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        await Crawler.register_crawl(url, "HTTP_GET")
        ranking_img = soup.find("div", class_="EntryBody").find("a").get("href")
        ranking_image_size = await Crawler.try_to_get_image_size(ranking_img)
        await Crawler.register_crawl(ranking_img, "HTTP_GET")
        await UseMySQL.run_sql(
            "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
            (url, new_article["title"], new_article["category"], SERVICE_NAME),
        )
        await UseMySQL.run_sql(
            "INSERT INTO sent_images (url, original_url, category, service, width, height) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                ranking_img,
                url,
                new_article["category"],
                SERVICE_NAME,
                ranking_image_size[0],
                ranking_image_size[1],
            ),
        )
        await client.get_channel(DISCORD_INFO_CHANNEL_ID).send(ranking_img)
        return

    @staticmethod
    async def parse_many_cs_results(new_article: dict):
        sent_urls = await UseMySQL.run_sql(
            "SELECT url FROM sent_urls WHERE service = %s AND category = 'many_cs_results'",
            (SERVICE_NAME,),
        )
        url = new_article["url"]
        # パースは一回でOK
        if url in sent_urls:
            return
        # 中身までは見ない(現状)
        await UseMySQL.run_sql(
            "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
            (url, new_article["title"], new_article["category"], SERVICE_NAME),
        )
        await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(url)
        return

    @staticmethod
    async def parse_hatti_cs_result(new_article: dict):
        sent_urls = await UseMySQL.run_sql(
            "SELECT url FROM sent_urls WHERE service = %s AND category = 'hatti_cs_result'",
            (SERVICE_NAME,),
        )
        url = new_article["url"]
        category = new_article["category"]
        # パースは一回でOK
        if url in sent_urls:
            return
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        await Crawler.register_crawl(url, "HTTP_GET")
        divisions = soup.find_all("div", class_="caption_white")
        result_div = divisions[0]
        for br in result_div.find_all("br"):
            br.replace_with("\n")
        result_sentence = result_div.text
        names_div = divisions[1]
        for br in names_div.find_all("br"):
            br.replace_with("\n")
        names = names_div.text
        relate_url_div = soup.find("div", class_="EntryMore").find_all("a")
        relate_urls = [
            relate_url.get("href")
            for relate_url in relate_url_div
            if relate_url.get("href") is not None
        ]
        result_url = ""
        images = []
        for relate_url in relate_urls:
            if "https://hattics.jp" in relate_url:
                result_url = relate_url
                break
        if result_url == "":
            blockquote_divs = soup.find_all("blockquote")
            for blockquote_div in blockquote_divs:
                a_tags = blockquote_div.find_all("a")
                for a_tag in a_tags:
                    href = a_tag.get("href")
                    if href and "https://t.co" in href:
                        result_url = href
                        break
                if result_url != "":
                    break
        if result_url != "":
            soup = await Crawler.try_to_get_soup(result_url)
            if soup == "FAILED":
                return
            await Crawler.register_crawl(result_url, "HTTP_GET")
            figures = soup.find_all("figure", class_="wp-block-image")
            images = [
                figure.find("img").get("src")
                for figure in figures
                if figure.find("img") is not None
            ]
            if images == []:
                figures = soup.find_all("div", class_="wp-block-image")
                images = [
                    figure.find("img").get("src")
                    for figure in figures
                    if figure.find("img") is not None
                ]
            # チーム戦などの場合
            if images == []:
                figures = soup.find_all("li", class_="wp-block-jetpack-slideshow_slide")
                images = [
                    figure.find("img").get("src")
                    for figure in figures
                    if figure.find("img") is not None
                ]
            else:
                if not await Logic.judge_isimage(images[0]):
                    figures = soup.find_all(
                        "li", class_="wp-block-jetpack-slideshow_slide"
                    )
                    images = [
                        figure.find("img").get("src")
                        for figure in figures
                        if figure.find("img") is not None
                    ]
        else:
            # はっちCSが協賛している別のCSの場合
            new_article["category"] = "cs_result"
            await Parser.parse_cs_result(new_article)
            return
        await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(
            f"{result_sentence}\n\n{names}"
        )
        await UseMySQL.run_sql(
            "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
            (url, new_article["title"], category, SERVICE_NAME),
        )
        await Logic.send_result_images(images, url, category)
        return

    @staticmethod
    async def parse_gp_result(new_article: dict):
        sent_urls = await UseMySQL.run_sql(
            "SELECT url FROM sent_urls WHERE service = %s AND category = 'gp_result'",
            (SERVICE_NAME,),
        )
        url = new_article["url"]
        category = new_article["category"]
        # パースは一回でOK
        if url in sent_urls:
            return
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        await Crawler.register_crawl(url, "HTTP_GET")
        divisions = soup.find_all("div", class_="caption_white")
        if len(divisions) < 2:
            # 記事が完成していない
            return
        result_div = divisions[0]
        for br in result_div.find_all("br"):
            br.replace_with("\n")
        result_sentence = result_div.text
        names_div = divisions[1]
        for br in names_div.find_all("br"):
            br.replace_with("\n")
        names = names_div.text
        distribution = ""
        if len(divisions) > 2:
            distribution_div = divisions[2]
            for br in distribution_div.find_all("br"):
                br.replace_with("\n")
            distribution = distribution_div.text
        imgs = soup.find_all("div", class_="dm_deck_image")
        images = [
            img.find("img").get("src") for img in imgs if img.find("img") is not None
        ]
        if images == []:
            # デッキ画像がない
            return
        await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(
            f"{result_sentence}\n\n{names}\n\n{distribution}"
        )
        await UseMySQL.run_sql(
            "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
            (url, new_article["title"], category, SERVICE_NAME),
        )
        await Logic.send_result_images(images, url, category)
        return

    @staticmethod
    async def parse_cs_result(new_article: dict):
        sent_urls = await UseMySQL.run_sql(
            "SELECT url FROM sent_urls WHERE service = %s AND category = 'cs_result'",
            (SERVICE_NAME,),
        )
        url = new_article["url"]
        category = new_article["category"]
        # パースは一回でOK
        if url in sent_urls:
            return
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        await Crawler.register_crawl(url, "HTTP_GET")
        divisions = soup.find_all("div", class_="caption_white")
        result_div = divisions[0]
        for br in result_div.find_all("br"):
            br.replace_with("\n")
        result_sentence = result_div.text
        if len(divisions) < 2:
            names = ""
        else:
            names_div = divisions[1]
            for br in names_div.find_all("br"):
                br.replace_with("\n")
            names = names_div.text
        imgs = soup.find_all("div", class_="dm_deck_image")
        images = [
            img.find("img").get("src") for img in imgs if img.find("img") is not None
        ]
        await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(
            f"{result_sentence}\n\n{names}"
        )
        await UseMySQL.run_sql(
            "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
            (url, new_article["title"], category, SERVICE_NAME),
        )
        await Logic.send_result_images(images, url, category)
        return

    @staticmethod
    async def parse_new_card(new_article: dict):
        url = new_article["url"]
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        await Crawler.register_crawl(url, "HTTP_GET")
        is_new_url = (
            await UseMySQL.run_sql(
                "SELECT url FROM sent_urls WHERE service = %s AND category = 'new_card' AND url = %s",
                (SERVICE_NAME, url),
            )
            == []
        )
        # 1回だけ追加する
        if is_new_url:
            await UseMySQL.run_sql(
                "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
                (
                    url,
                    new_article["title"],
                    new_article["category"],
                    SERVICE_NAME,
                ),
            )
        newcard_img_divs = soup.find_all("div", class_="card_image")
        newcard_images = []
        for newcard_img_div in newcard_img_divs:
            img_tags = newcard_img_div.find_all("img")
            for img_tag in img_tags:
                img_src = img_tag.get("src")
                if img_src:
                    newcard_images.append(img_src)
        if newcard_images == []:
            newcard_img_divs = soup.find("div", class_="EntryMore").find_all("img")
            newcard_images = [
                newcard_img.get("src")
                for newcard_img in newcard_img_divs
                if newcard_img.get("src") is not None
            ]
        newcard_images = list(set(newcard_images))
        await Logic.send_new_info_images(newcard_images, url, new_article["category"])
        return

    async def parse_stream(new_article: dict):
        url = new_article["url"]
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        await Crawler.register_crawl(url, "HTTP_GET")
        is_new_url = (
            await UseMySQL.run_sql(
                "SELECT url FROM sent_urls WHERE service = %s AND category = 'stream' AND url = %s",
                (SERVICE_NAME, url),
            )
            == []
        )
        # 1回だけ追加する
        if is_new_url:
            await UseMySQL.run_sql(
                "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
                (
                    url,
                    new_article["title"],
                    new_article["category"],
                    SERVICE_NAME,
                ),
            )
        streamed_imgs = soup.find("div", class_="EntryMore").find_all("img")
        streamed_images = [
            streamed_img.get("src")
            for streamed_img in streamed_imgs
            if streamed_img.get("src") is not None
        ]
        await Logic.send_new_info_images(streamed_images, url, new_article["category"])
        return


async def main():
    while True:
        try:
            new_articles = await Crawler.get_new_articles()
            for new_article in new_articles:
                await Logic.decide_parser(new_article)
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
