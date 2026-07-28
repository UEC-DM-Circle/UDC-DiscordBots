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
        # 3ヶ月以内に同じURLが送信されていないか
        return (
            await UseMySQL.run_sql(
                """
                SELECT 1 FROM sent_urls su
                JOIN services s ON su.service_id = s.id
                JOIN categories c ON su.category_id = c.id
                WHERE s.name = %s AND c.name = %s AND su.url = %s AND su.created_at >= DATE_SUB(NOW(), INTERVAL 3 MONTH)
                LIMIT 1
                """,
                (SERVICE_NAME, category, url),
            )
            != []
        )

    @staticmethod
    async def judge_issent(url: str, category: str) -> bool:
        # 3ヶ月以内に同じ画像が送信されていないか
        return (
            await UseMySQL.run_sql(
                """
                SELECT 1 FROM sent_images si
                JOIN services s ON si.service_id = s.id
                JOIN categories c ON si.category_id = c.id
                WHERE s.name = %s AND c.name = %s AND si.url = %s AND si.created_at >= DATE_SUB(NOW(), INTERVAL 3 MONTH)
                LIMIT 1
                """,
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
            if "流星CS" in title:
                # https://supersolenoid.jp/blog-entry-46417.html
                return "ryusei_cs_result"
            if "DMGP" in title:
                # https://supersolenoid.jp/blog-entry-42560.html
                return "gp_result"
            # https://supersolenoid.jp/blog-entry-42770.html
            return "cs_result"
        if "DMGP" in title:
            # https://supersolenoid.jp/blog-entry-46211.html
            return "gp_result"
        if any(x in title for x in ("新情報まとめ", "最新情報")):
            # https://supersolenoid.jp/blog-entry-45500.html
            return "stream"
        if all(x in title for x in ("デッキ", "公開")):
            # https://supersolenoid.jp/blog-entry-45795.html
            return "stream"
        if "金トレジャー" in title:
            # https://supersolenoid.jp/blog-entry-46329.html
            # ↑との間違いに注意
            # https://supersolenoid.jp/blog-entry-45189.html
            if "収録カードまとめ" not in title:
                return "gold_treasure"
        return "etc"

    @staticmethod
    async def judge_deneblog_category(title: str) -> str:
        # デネブログでは金トレジャーをパースしない
        if "金トレジャー" in title:
            return "etc"
        if any(x in title for x in ("が公開", "》", "神アート", "公開情報まとめ")):
            # https://deneblog.jp/blog-entry-22499.html
            # https://deneblog.jp/blog-entry-22329.html
            return "new_card"
        # if "情報まとめ" in title:
        #     # https://deneblog.jp/blog-entry-22540.html
        #     return "stream"
        return "etc"
