import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
from PIL import Image
import mysql.connector
import asyncio
import os
import traceback

TOKEN = os.getenv("TOKEN")
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
    def get_connection():
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )

    async def run_sql(sql: str, params: tuple):
        conn = UseMySQL.get_connection()
        cursor = conn.cursor(buffered=True)
        if params != ():
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        if sql.strip().upper().startswith("SELECT"):
            result = await Logic.clean_list(cursor.fetchall())
            cursor.close()
            conn.close()
            return result
        else:
            conn.commit()
            cursor.close()
            conn.close()
            return


class Logic:
    async def clean_list(lst: list):
        for i in range(len(lst)):
            if type(lst[i]) is tuple:
                lst[i] = lst[i][0]
        return lst

    async def judge_category(title: str):
        if "入賞数ランキング" in title:
            return "ranking"
        elif "結果" in title:
            if "など大会結果" in title:
                # https://supersolenoid.jp/blog-entry-42601.html
                return "many_cs_results"
            elif "はっちCS" in title:
                # https://supersolenoid.jp/blog-entry-42779.html
                # https://supersolenoid.jp/blog-entry-42860.html
                # https://supersolenoid.jp/blog-entry-42944.html
                return "hatti_cs_result"
            elif "DMGP" in title:
                # https://supersolenoid.jp/blog-entry-42560.html
                return "gp_result"
            # https://supersolenoid.jp/blog-entry-42770.html
            return "cs_result"
        elif "が公開" in title or "多数公開" in title or "が判明" in title:
            # https://supersolenoid.jp/blog-entry-42669.html
            return "new_card"
        elif "新情報まとめ" in title:
            # https://supersolenoid.jp/blog-entry-42757.html
            return "stream"
        else:
            return "etc"

    async def send_result_images(result_images: list, url: str, category: str):
        for result_image in result_images:
            if not await Logic.judge_isimage(result_image):
                continue
            sent_images = await UseMySQL.run_sql(
                "SELECT url FROM sent_images WHERE service = 'UDC_Information'  AND original_url = %s",
                (url,),
            )
            if result_image in sent_images:
                continue
            deck_image_size = await Crawler.try_to_get_image_size(result_image)
            await UseMySQL.run_sql(
                "INSERT INTO sent_images (url, original_url, category, service, width, height) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    result_image,
                    url,
                    category,
                    "UDC_Information",
                    deck_image_size[0],
                    deck_image_size[1],
                ),
            )
            await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(result_image)
        return

    async def send_new_info_images(new_info_images: list, url: str, category: str):
        for new_info_image in new_info_images:
            if not await Logic.judge_isimage(new_info_image):
                continue
            sent_images = await UseMySQL.run_sql(
                "SELECT url FROM sent_images WHERE service = 'UDC_Information'  AND (category = 'new_card' OR category = 'stream')",
                (),
            )
            if new_info_image in sent_images:
                # すでに送信済みの画像はスキップ
                continue
            newcard_image_size = await Crawler.try_to_get_image_size(new_info_image)
            # if newcard_image_size[0] >= 1500:
            #     # 横長画像は広告
            #     continue
            if (
                newcard_image_size[0] == newcard_image_size[1]
                and newcard_image_size[0] != 0
            ):
                # 正方形画像は広告
                continue
            await UseMySQL.run_sql(
                "INSERT INTO sent_images (url, original_url, category, service, width, height) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    new_info_image,
                    url,
                    category,
                    "UDC_Information",
                    newcard_image_size[0],
                    newcard_image_size[1],
                ),
            )
            await client.get_channel(DISCORD_NEWCARD_CHANNEL_ID).send(new_info_image)
        return

    async def judge_isimage(image: str):
        if image.startswith("https") and (
            ".jpg" in image or ".jpeg" in image or ".png" in image or ".gif" in image
        ):
            return True
        return False


class Crawler:
    async def get_image_size(url: str):
        try:
            await asyncio.sleep(1)
            response = requests.get(url, stream=True).raw
            image = Image.open(response)
            image.verify()
            width, height = image.size
            return (width, height)
        except:
            return "ERROR"

    async def try_to_get_image_size(url: str, retries: int = 5):
        for _ in range(retries):
            size = await Crawler.get_image_size(url)
            if size != "ERROR":
                return size
        return (0, 0)  # サイズが見つからない場合は(0, 0)を返す

    async def get_soup(url: str):
        try:
            await asyncio.sleep(1)
            response = requests.get(url)
            if response.status_code == 200:
                return BeautifulSoup(response.text, "html.parser")
            else:
                return "ERROR"
        except:
            return "ERROR"

    async def try_to_get_soup(url: str, retries: int = 5):
        for _ in range(retries):
            soup = await Crawler.get_soup(url)
            if soup != "ERROR":
                return soup
        return "FAILED"

    async def get_new_articles():
        soup = await Crawler.try_to_get_soup(
            "https://supersolenoid.jp/blog-category-12.html"
        )
        if soup == "FAILED":
            return []
        article = soup.find_all("div", class_="EntryTitle")
        articles = []
        for a in article:
            articles.append(a.find("a").get("href"))
        article_title = soup.find_all("div", class_="EntryTitle")
        new_articles = []
        for i in range(len(articles)):
            url = articles[i]
            title = article_title[i].text
            category = await Logic.judge_category(title)
            new_articles.append(
                {
                    "url": url,
                    "title": title,
                    "category": category,
                }
            )
        return new_articles


class Parser:
    async def parse_ranking(new_article: dict):
        sent_urls = await UseMySQL.run_sql(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'ranking'",
            (),
        )
        url = new_article["url"]
        # パースは一回でOK
        if url in sent_urls:
            return
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        ranking_img = soup.find("div", class_="EntryBody").find("a").get("href")
        ranking_image_size = await Crawler.try_to_get_image_size(ranking_img)
        await UseMySQL.run_sql(
            "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
            (url, new_article["title"], new_article["category"], "UDC_Information"),
        )
        await UseMySQL.run_sql(
            "INSERT INTO sent_images (url, original_url, category, service, width, height) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                ranking_img,
                url,
                new_article["category"],
                "UDC_Information",
                ranking_image_size[0],
                ranking_image_size[1],
            ),
        )
        await client.get_channel(DISCORD_INFO_CHANNEL_ID).send(ranking_img)
        return

    async def parse_many_cs_results(new_article: dict):
        sent_urls = await UseMySQL.run_sql(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'many_cs_results'",
            (),
        )
        url = new_article["url"]
        # パースは一回でOK
        if url in sent_urls:
            return
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        await UseMySQL.run_sql(
            "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
            (url, new_article["title"], new_article["category"], "UDC_Information"),
        )
        await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(url)
        return

    async def parse_hatti_cs_result(new_article: dict):
        sent_urls = await UseMySQL.run_sql(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'hatti_cs_result'",
            (),
        )
        url = new_article["url"]
        category = new_article["category"]
        # パースは一回でOK
        if url in sent_urls:
            return
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
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
        if result_url != "":
            soup = await Crawler.try_to_get_soup(result_url)
            if soup != "FAILED":
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
                    figures = soup.find_all(
                        "li", class_="wp-block-jetpack-slideshow_slide"
                    )
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
            (url, new_article["title"], category, "UDC_Information"),
        )
        await Logic.send_result_images(images, url, category)
        return

    async def parse_gp_result(new_article: dict):
        sent_urls = await UseMySQL.run_sql(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'gp_result'",
            (),
        )
        url = new_article["url"]
        category = new_article["category"]
        # パースは一回でOK
        if url in sent_urls:
            return
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        divisions = soup.find_all("div", class_="caption_white")
        if len(divisions) < 3:
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
            (url, new_article["title"], category, "UDC_Information"),
        )
        await Logic.send_result_images(images, url, category)
        return

    async def parse_cs_result(new_article: dict):
        sent_urls = await UseMySQL.run_sql(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'cs_result'",
            (),
        )
        url = new_article["url"]
        category = new_article["category"]
        # パースは一回でOK
        if url in sent_urls:
            return
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
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
            (url, new_article["title"], category, "UDC_Information"),
        )
        await Logic.send_result_images(images, url, category)
        return

    async def parse_new_card(new_article: dict):
        url = new_article["url"]
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        sent_urls = await UseMySQL.run_sql(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'new_card'",
            (),
        )
        # 1回だけ追加する
        if url not in sent_urls:
            await UseMySQL.run_sql(
                "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
                (
                    url,
                    new_article["title"],
                    new_article["category"],
                    "UDC_Information",
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
        sent_urls = await UseMySQL.run_sql(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'stream'",
            (),
        )
        # 1回だけ追加する
        if url not in sent_urls:
            await UseMySQL.run_sql(
                "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
                (
                    url,
                    new_article["title"],
                    new_article["category"],
                    "UDC_Information",
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
    print("Bot is ready!")
    if task is None or task.done():
        task = asyncio.create_task(main())


client.run(TOKEN)
