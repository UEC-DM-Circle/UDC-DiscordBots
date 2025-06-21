import discord
from discord.ext import commands
import requests
from bs4 import BeautifulSoup
from PIL import Image
import mysql.connector
import asyncio
import os
import time

TOKEN = os.getenv("TOKEN")
# 入賞数ランキング
DISCORD_INFO_CHANNEL_ID = int(os.environ.get("DISCORD_INFO_CHANNEL_ID"))
# 新カード
DISCORD_NEWCARD_CHANNEL_ID = int(os.environ.get("DISCORD_NEWCARD_CHANNEL_ID"))
# CS結果
DISCORD_RESULT_CHANNEL_ID = int(os.environ.get("DISCORD_RESULT_CHANNEL_ID"))
intent = discord.Intents.default()
intent.message_content = True
client = commands.Bot(command_prefix="-", intents=intent)

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    username=os.getenv("DB_USERNAME"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
)
cursor = conn.cursor(buffered=True)


async def clean_list(lst: list):
    for i in range(len(lst)):
        if type(lst[i]) is tuple:
            lst[i] = lst[i][0]
    return lst


async def judge_article_title(title: str):
    if "入賞数ランキング" in title:
        return "ranking"
    elif "結果" in title:
        if "など大会結果" in title:
            # https://supersolenoid.jp/blog-entry-42601.html
            return "cs_result_many"
        elif "はっち" in title:
            # https://supersolenoid.jp/blog-entry-42779.html
            return "cs_result_hatti"
        elif "DMGP" in title:
            # https://supersolenoid.jp/blog-entry-42560.html
            return "gp_result"
        # https://supersolenoid.jp/blog-entry-42770.html
        return "cs_result"
    elif "が" in title and "公開" in title:
        # https://supersolenoid.jp/blog-entry-42669.html
        return "new_card"
    elif "新情報まとめ" in title:
        # https://supersolenoid.jp/blog-entry-42757.html
        return "stream"
    else:
        return "etc"


class Crawler:
    async def get_image_size(url: str):
        try:
            asyncio.sleep(1)
            response = requests.get(url, stream=True).raw
            image = Image.open(response)
            image.verify()
            width, height = image.size
            return (width, height)
        except:
            return "ERROR"

    async def try_to_get_image_size(url: str, retries: int = 5):
        for attempt in range(retries):
            size = await Crawler.get_image_size(url)
            if size != "ERROR":
                return size
        return (0, 0)  # サイズが見つからない場合は(0, 0)を返す

    async def get_soup(url: str):
        try:
            asyncio.sleep(1)
            response = requests.get(url)
            if response.status_code == 200:
                return BeautifulSoup(response.text, "html.parser")
            else:
                return "ERROR"
        except:
            return "ERROR"

    async def try_to_get_soup(url: str, retries: int = 5):
        for attempt in range(retries):
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
            article_type = await judge_article_title(title)
            new_articles.append(
                {
                    "url": url,
                    "title": title,
                    "article_type": article_type,
                }
            )
        return new_articles


class Parser:
    async def parse_ranking(new_article: dict):
        cursor.execute(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'ranking'"
        )
        sent_urls = await clean_list(cursor.fetchall())
        url = new_article["url"]
        # パースは一回でOK
        if url in sent_urls:
            return
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        ranking_img = soup.find("div", class_="EntryBody").find("a").get("href")
        ranking_image_size = await Crawler.try_to_get_image_size(ranking_img)
        cursor.execute(
            "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
            (url, new_article["title"], new_article["article_type"], "UDC_Information"),
        )
        conn.commit()
        cursor.execute(
            "INSERT INTO sent_images (url, original_url, category, service, width, height) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                ranking_img,
                url,
                new_article["article_type"],
                "UDC_Information",
                ranking_image_size[0],
                ranking_image_size[1],
            ),
        )
        conn.commit()
        # await client.get_channel(DISCORD_INFO_CHANNEL_ID).send(ranking_img)
        return

    async def parse_cs_result_many(new_article: dict):
        cursor.execute(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'cs_result_many'"
        )
        sent_urls = await clean_list(cursor.fetchall())
        url = new_article["url"]
        # パースは一回でOK
        if url in sent_urls:
            return
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        cursor.execute(
            "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
            (url, new_article["title"], new_article["article_type"], "UDC_Information"),
        )
        conn.commit()
        # await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(url)
        return

    async def parse_cs_result_hatti(new_article: dict):
        cursor.execute(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'cs_result_hatti'"
        )
        sent_urls = await clean_list(cursor.fetchall())
        url = new_article["url"]
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
        # await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(
        #     f"{result_sentence}\n\n{names}"
        # )
        cursor.execute(
            "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
            (url, new_article["title"], new_article["article_type"], "UDC_Information"),
        )
        conn.commit()
        for image in images:
            print(image)
            deck_image_size = await Crawler.try_to_get_image_size(image)
            # await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(image)
            cursor.execute(
                "INSERT INTO sent_images (url, original_url, category, service, width, height) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    image,
                    result_url,
                    new_article["article_type"],
                    "UDC_Information",
                    deck_image_size[0],
                    deck_image_size[1],
                ),
            )
            conn.commit()
        return

    async def parse_gp_result(new_article: dict):
        cursor.execute(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'gp_result'"
        )
        sent_urls = await clean_list(cursor.fetchall())
        url = new_article["url"]
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
        # await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(
        #     f"{result_sentence}\n\n{names}\n\n{distribution}"
        # )
        cursor.execute(
            "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
            (url, new_article["title"], new_article["article_type"], "UDC_Information"),
        )
        conn.commit()
        for image in images:
            deck_image_size = await Crawler.try_to_get_image_size(image)
            # await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(image)
            cursor.execute(
                "INSERT INTO sent_images (url, original_url, category, service, width, height) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    image,
                    url,
                    new_article["article_type"],
                    "UDC_Information",
                    deck_image_size[0],
                    deck_image_size[1],
                ),
            )
            conn.commit()
        return

    async def parse_cs_result(new_article: dict):
        cursor.execute(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'cs_result'"
        )
        sent_urls = await clean_list(cursor.fetchall())
        url = new_article["url"]
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
        imgs = soup.find_all("div", class_="dm_deck_image")
        images = [
            img.find("img").get("src") for img in imgs if img.find("img") is not None
        ]
        # await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(
        #     f"{result_sentence}\n\n{names}"
        # )
        cursor.execute(
            "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
            (url, new_article["title"], new_article["article_type"], "UDC_Information"),
        )
        conn.commit()
        for image in images:
            deck_image_size = await Crawler.try_to_get_image_size(image)
            # await client.get_channel(DISCORD_RESULT_CHANNEL_ID).send(image)
            cursor.execute(
                "INSERT INTO sent_images (url, original_url, category, service, width, height) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    image,
                    url,
                    new_article["article_type"],
                    "UDC_Information",
                    deck_image_size[0],
                    deck_image_size[1],
                ),
            )
            conn.commit()
        return

    async def parse_new_card(new_article: dict):
        url = new_article["url"]
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        cursor.execute(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'new_card'"
        )
        sent_urls = await clean_list(cursor.fetchall())
        # 1回だけ追加する
        if url not in sent_urls:
            cursor.execute(
                "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
                (
                    url,
                    new_article["title"],
                    new_article["article_type"],
                    "UDC_Information",
                ),
            )
            conn.commit()
        newcard_imgs = soup.find_all("div", class_="card_image")
        newcard_images = [
            newcard_img.find("img").get("src")
            for newcard_img in newcard_imgs
            if newcard_img.find("img") is not None
        ]
        if newcard_images == []:
            newcard_imgs = soup.find("div", class_="EntryMore").find_all("img")
            newcard_image = [
                newcard_img.get("src")
                for newcard_img in newcard_imgs
                if newcard_img.get("src") is not None
            ]
        cursor.execute(
            "SELECT url FROM sent_images WHERE service = 'UDC_Information' AND category = 'new_card'"
        )
        sent_images = await clean_list(cursor.fetchall())
        for newcard_image in newcard_images:
            if newcard_image in sent_images:
                # すでに送信済みの画像はスキップ
                continue
            if "evwoh" in newcard_image:
                # evwohが含まれている画像は広告
                continue
            newcard_image_size = await Crawler.try_to_get_image_size(newcard_image)
            if newcard_image_size[0] >= 1500:
                # 横長画像は広告
                continue
            if (
                newcard_image_size[0] == newcard_image_size[1]
                and newcard_image_size[0] != 0
            ):
                # 正方形画像は広告
                continue
            # await client.get_channel(DISCORD_NEWCARD_CHANNEL_ID).send(newcard_image)
            cursor.execute(
                "INSERT INTO sent_images (url, original_url, category, service, width, height) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    newcard_image,
                    url,
                    new_article["article_type"],
                    "UDC_Information",
                    newcard_image_size[0],
                    newcard_image_size[1],
                ),
            )
            conn.commit()
        return

    async def parse_stream(new_article: dict):
        url = new_article["url"]
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        cursor.execute(
            "SELECT url FROM sent_urls WHERE service = 'UDC_Information' AND category = 'stream'"
        )
        sent_urls = await clean_list(cursor.fetchall())
        # 1回だけ追加する
        if url not in sent_urls:
            cursor.execute(
                "INSERT INTO sent_urls (url, title, category, service) VALUES (%s, %s, %s, %s)",
                (
                    url,
                    new_article["title"],
                    new_article["article_type"],
                    "UDC_Information",
                ),
            )
            conn.commit()
        streamed_imgs = soup.find("div", class_="EntryMore").find_all("img")
        streamed_images = [
            streamed_img.get("src")
            for streamed_img in streamed_imgs
            if streamed_img.get("src") is not None
        ]
        cursor.execute(
            "SELECT url FROM sent_images WHERE service = 'UDC_Information'  AND category = 'stream'"
        )
        sent_images = await clean_list(cursor.fetchall())
        for streamed_image in streamed_images:
            if streamed_image in sent_images:
                # すでに送信済みの画像はスキップ
                continue
            if "evwoh" in streamed_image:
                # evwohが含まれている画像は広告
                continue
            streamed_image_size = await Crawler.try_to_get_image_size(streamed_image)
            if streamed_image_size[0] >= 1500:
                # 横長画像は広告
                continue
            if (
                streamed_image_size[0] == streamed_image_size[1]
                and streamed_image_size[0] != 0
            ):
                # 正方形画像は広告
                continue
            # await client.get_channel(DISCORD_INFO_CHANNEL_ID).send(streamed_image)
            cursor.execute(
                "INSERT INTO sent_images (url, original_url, category, service, width, height) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    streamed_image,
                    url,
                    new_article["article_type"],
                    "UDC_Information",
                    streamed_image_size[0],
                    streamed_image_size[1],
                ),
            )
            conn.commit()


async def main():
    new_articles = await Crawler.get_new_articles()
    for new_article in new_articles:
        match new_article["article_type"]:
            case "ranking":
                await Parser.parse_ranking(new_article)
            case "cs_result_many":
                await Parser.parse_cs_result_many(new_article)
            case "cs_result_hatti":
                await Parser.parse_cs_result_hatti(new_article)
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


@client.command()
async def test(ctx):
    if ctx.channel.id == DISCORD_INFO_CHANNEL_ID:
        await ctx.send("Information bot is working!")


@client.event
async def on_ready():
    while True:
        await main()
        await asyncio.sleep(60)


client.run(TOKEN)
