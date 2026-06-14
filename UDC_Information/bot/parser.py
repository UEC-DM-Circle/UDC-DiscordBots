from common import *
from crawler import Crawler
from logic import Logic
from use_mysql import UseMySQL


class Parser:
    # 全体的に共通部分をまとめる
    @staticmethod
    async def parse_ranking(new_article: dict) -> str:
        url = new_article["url"]
        title = new_article["title"]
        category = new_article["category"]
        service_id = await Crawler.retrive_id("services", SERVICE_NAME)
        category_id = await Crawler.retrive_id("categories", category)
        if service_id is None or category_id is None:
            return
        # パースは一回でOK
        if await Logic.judge_iscrawled(url, category):
            return
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return
        await Crawler.register_crawl(url, "HTTP_GET")
        ranking_img = soup.find("div", class_="EntryBody").find("a").get("href")
        ranking_image_size = await Crawler.try_to_get_image_size(ranking_img)
        await Crawler.register_crawl(ranking_img, "HTTP_GET")
        await UseMySQL.run_sql(
            "INSERT INTO sent_urls (url, title, category_id, service_id) VALUES (%s, %s, %s, %s)",
            (url, title, category_id, service_id),
        )
        original_url_id = await UseMySQL.run_sql(
            "SELECT id FROM sent_urls WHERE url = %s AND category_id = %s AND service_id = %s ORDER BY id DESC LIMIT 1",
            (url, category_id, service_id),
        )
        if original_url_id == []:
            return
        original_url_id = original_url_id[0]
        await UseMySQL.run_sql(
            "INSERT INTO sent_images (url, original_url_id, category_id, service_id, width, height) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                ranking_img,
                original_url_id,
                category_id,
                service_id,
                ranking_image_size[0],
                ranking_image_size[1],
            ),
        )
        return ranking_img

    @staticmethod
    async def parse_soup_of_many_cs_results(soup: BeautifulSoup) -> list:
        entries = soup.find("div", class_="EntryMore")
        overviews_or_embed_tweets = entries.find_all(
            ["div", "blockquote"], attrs={"class": ["caption_white", "twitter-tweet"]}
        )
        cs_results = []
        for overview_or_embed_tweet in overviews_or_embed_tweets:
            if "caption_white" in overview_or_embed_tweet.get("class", []):
                # 大会概要
                for br in overview_or_embed_tweet.find_all("br"):
                    br.replace_with("\n")
                result_sentence = overview_or_embed_tweet.text.strip()
                cs_results.append(
                    {
                        "result_sentence": result_sentence,
                        "result_tweets": [],
                        "tweet_texts": [],
                    }
                )
            elif "twitter-tweet" in overview_or_embed_tweet.get("class", []):
                # 埋め込みツイート
                for br in overview_or_embed_tweet.find_all("br"):
                    br.replace_with(" ")
                a_tags = overview_or_embed_tweet.find_all("a")
                tweet_urls = [
                    a_tag.get("href").split("?")[0]
                    for a_tag in a_tags
                    if a_tag.get("href") is not None
                    and "status" in a_tag.get("href")
                    and not a_tag.get("href").startswith("https://twitter.com/hashtag/")
                    and not a_tag.get("href").startswith("https://x.com/hashtag/")
                    and not a_tag.get("href").startswith("https://t.co/")
                ]
                tweet_texts = overview_or_embed_tweet.find_all("p")
                tweet_texts = [tweet_text.text.strip() for tweet_text in tweet_texts]
                if tweet_urls:
                    cs_results[-1]["result_tweets"] += tweet_urls
                    cs_results[-1]["tweet_texts"] += tweet_texts
        return cs_results

    @staticmethod
    async def parse_many_cs_results(new_article: dict) -> list:
        url = new_article["url"]
        category = new_article["category"]
        # パースは一回でOK
        if await Logic.judge_iscrawled(url, category):
            return []
        # 中身を見て、大会情報を抜き出す！
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return []
        await Crawler.register_crawl(url, "HTTP_GET")
        return await Parser.parse_soup_of_many_cs_results(soup)

    @staticmethod
    async def parse_hatti_cs_result(new_article: dict):
        url = new_article["url"]
        category = new_article["category"]
        # パースは一回でOK
        if await Logic.judge_iscrawled(url, category):
            return "", []
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return "", []
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
            hatti_base_url = "https://cardshop-hatti.jp"
            figures = soup.find_all("figure", class_="inner_item_img")
            images = [
                hatti_base_url + figure.find("img").get("src")
                for figure in figures
                if figure.find("img") is not None
            ]
            if images == []:
                figures = soup.find_all("div", class_="inner_item_img")
                images = [
                    hatti_base_url + figure.find("img").get("src")
                    for figure in figures
                    if figure.find("img") is not None
                ]
            # チーム戦などの場合
            # 要対応！
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
            return await Parser.parse_cs_result(new_article)
        return f"{result_sentence}\n\n{names}", images

    @staticmethod
    async def parse_ryusei_cs_result(new_article: dict):
        url = new_article["url"]
        category = new_article["category"]
        # パースは一回でOK
        if await Logic.judge_iscrawled(url, category):
            return "", []
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return "", []
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
            if "https://harutomoshi-channel.com/" in relate_url:
                result_url = relate_url
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
            # 最後の一個は次回予告なので除外する
            images = images[:-1]
            # チーム戦などの場合があれば対応する
        else:
            # 流星CSが協賛している別のCSの場合
            new_article["category"] = "cs_result"
            return await Parser.parse_cs_result(new_article)
        return f"{result_sentence}\n\n{names}", images

    @staticmethod
    async def parse_gp_result(new_article: dict):
        url = new_article["url"]
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return "", []
        await Crawler.register_crawl(url, "HTTP_GET")
        divisions = soup.find_all("div", class_="caption_white")
        if len(divisions) < 2:
            # 記事が完成していない
            return "", []
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
        return f"{result_sentence}\n\n{names}\n\n{distribution}", images

    @staticmethod
    async def parse_cs_result(new_article: dict):
        url = new_article["url"]
        category = new_article["category"]
        # パースは一回でOK
        if await Logic.judge_iscrawled(url, category):
            return "", []
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return "", []
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
        return f"{result_sentence}\n\n{names}", images

    @staticmethod
    async def parse_gold_treasure(new_article: dict):
        url = new_article["url"]
        title = new_article["title"]
        category = new_article["category"]
        service_id = await Crawler.retrive_id("services", SERVICE_NAME)
        category_id = await Crawler.retrive_id("categories", category)
        if service_id is None or category_id is None:
            return []
        # パースは一回でOK
        if await Logic.judge_iscrawled(url, category):
            return []
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return []
        await Crawler.register_crawl(url, "HTTP_GET")
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
        await UseMySQL.run_sql(
            "INSERT INTO sent_urls (url, title, category_id, service_id) VALUES (%s, %s, %s, %s)",
            (url, title, category_id, service_id),
        )
        return sorted(list(set(newcard_images)))

    async def parse_stream(new_article: dict):
        url = new_article["url"]
        title = new_article["title"]
        category = new_article["category"]
        service_id = await Crawler.retrive_id("services", SERVICE_NAME)
        category_id = await Crawler.retrive_id("categories", category)
        if service_id is None or category_id is None:
            return []
        # 1回だけ追加する
        if not await Logic.judge_iscrawled(url, category):
            await UseMySQL.run_sql(
                "INSERT INTO sent_urls (url, title, category_id, service_id) VALUES (%s, %s, %s, %s)",
                (
                    url,
                    title,
                    category_id,
                    service_id,
                ),
            )
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return []
        await Crawler.register_crawl(url, "HTTP_GET")
        streamed_imgs = soup.find("div", class_="EntryMore").find_all("img")
        streamed_images = [
            streamed_img.get("src")
            for streamed_img in streamed_imgs
            if streamed_img.get("src") is not None
        ]
        return sorted(list(set(streamed_images)))

    @staticmethod
    async def parse_deneblog_images(url: str) -> list:
        soup = await Crawler.try_to_get_soup(url)
        if soup == "FAILED":
            return []
        await Crawler.register_crawl(url, "HTTP_GET")
        tablebox_div = soup.find("div", id="tablebox")
        if tablebox_div is None:
            return []
        deneblog_images = [
            img.get("src")
            for img in tablebox_div.find_all("img")
            if img.get("src") is not None
        ]
        return sorted(list(set(deneblog_images)))

    @staticmethod
    async def parse_new_card(new_article: dict):
        url = new_article["url"]
        category = new_article["category"]
        # パースは一回でOK
        if await Logic.judge_iscrawled(url, category):
            return []
        return await Parser.parse_deneblog_images(url)
