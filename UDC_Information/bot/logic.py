from common import *
from use_mysql import UseMySQL
from crawler import *
from parser import *


class Logic:
    @staticmethod
    async def judge_isimage(url: str) -> bool:
        return url.startswith("https") and any(
            ext in url for ext in (".jpg", ".jpeg", ".png", ".gif")
        )

    @staticmethod
    async def judge_iscrawled(url: str, category: str) -> bool:
        return (
            await UseMySQL.run_sql(
                "SELECT url FROM sent_urls WHERE service = %s AND category = %s AND url = %s",
                (SERVICE_NAME, category, url),
            )
            != []
        )

    @staticmethod
    async def judge_denen_category(title: str) -> str:
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
        if "金トレジャー" in title:
            # https://supersolenoid.jp/blog-entry-45189.html
            return "gold_treasure"
        return "etc"

    @staticmethod
    async def judge_deneblog_category(title: str) -> str:
        # デネブログでは金トレジャーをパースしない
        if "金トレジャー" in title:
            return "etc"
        if any(x in title for x in ("新カード", "》", "神アート")):
            # https://deneblog.jp/blog-entry-22499.html
            # https://deneblog.jp/blog-entry-22329.html
            return "new_card"
        if "新情報まとめ" in title:
            # https://deneblog.jp/blog-entry-22388.html
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
            case "gold_treasure":
                await Parser.parse_gold_treasure(new_article)
            case "new_card":
                await Parser.parse_new_card(new_article)
            case "stream":
                await Parser.parse_stream(new_article)
            case "etc":
                pass
