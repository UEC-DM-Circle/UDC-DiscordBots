from common import *
from use_mysql import UseMySQL


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
        if "新情報まとめ" in title:
            #
            return "stream"
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
        # if any(
        #     x in title for x in ("公開情報まとめ", "新情報まとめ", "新カードまとめ")
        # ):
        #     # https://deneblog.jp/blog-entry-22388.html
        #     return "stream"
        return "etc"
