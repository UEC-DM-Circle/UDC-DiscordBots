from common import *
from use_mysql import UseMySQL


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

    @staticmethod
    async def retrive_id(table_name: str, key: str):
        id = await UseMySQL.run_sql(
            "SELECT id FROM {} WHERE name = %s".format(table_name), (key,)
        )
        if not id:
            return None
        return id[0]

    @classmethod
    async def register_crawl(cls, target_url: str, crawl_method: str):
        crawl_method_id = await cls.retrive_id("crawl_methods", crawl_method)
        service_id = await cls.retrive_id("services", SERVICE_NAME)
        if crawl_method_id is None or service_id is None:
            return
        await UseMySQL.run_sql(
            "INSERT INTO crawls (target_url, crawl_method_id, service_id) VALUES (%s, %s, %s)",
            (target_url, crawl_method_id, service_id),
        )

    @classmethod
    async def register_api_status_code(cls, status_code: int, crawl_method: str):
        crawl_method_id = await cls.retrive_id("crawl_methods", crawl_method)
        service_id = await cls.retrive_id("services", SERVICE_NAME)
        if crawl_method_id is None or service_id is None:
            return
        latest_crawl_id = await UseMySQL.run_sql(
            "SELECT id FROM crawls WHERE crawl_method_id = %s AND service_id = %s ORDER BY created_at DESC LIMIT 1",
            (crawl_method_id, service_id),
        )
        if not latest_crawl_id:
            return
        await UseMySQL.run_sql(
            "INSERT INTO api_status_codes (crawl_id, status_code) VALUES (%s, %s)",
            (latest_crawl_id[0], status_code),
        )

    @classmethod
    async def check_latest_api_crawl_time(cls) -> bool:
        crawl_method_id = await cls.retrive_id("crawl_methods", "X_API")
        service_id = await cls.retrive_id("services", SERVICE_NAME)
        if crawl_method_id is None or service_id is None:
            return
        result = await UseMySQL.run_sql(
            "SELECT created_at FROM crawls WHERE crawl_method_id = %s AND service_id = %s ORDER BY created_at DESC LIMIT 1",
            (crawl_method_id, service_id),
        )
        # 初回クロールの場合はTrueを返す
        if not result:
            return True
        latest_clawl_time = result[0].timestamp()
        current_time = datetime.datetime.now().timestamp()
        # 最後のAPIを用いたクロールから15分経過しているか返す
        return current_time - latest_clawl_time > 60 * 15

    @classmethod
    async def fetch_latest_tweets(cls, max_results: int) -> list:
        retries = 5
        target_url = f"https://api.twitter.com/2/users/{TWITTER_USER_ID}/tweets"
        headers = {
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "User-Agent": "v2UserTweetsPython",
        }
        params = {"max_results": max_results, "tweet.fields": "text"}
        for attempt in range(retries):
            await asyncio.sleep(1)
            response = await cls.session.get(target_url, headers=headers, params=params)
            await cls.register_crawl(target_url, "X_API")
            await cls.register_api_status_code(response.status, "X_API")
            if response.status == 200:
                return (await response.json()).get("data", [])
            elif response.status == 429:
                await write_log_message("レート制限に到達しました。", "ERROR")
                await asyncio.sleep(200 * (attempt + 1))
            else:
                await write_log_message(
                    "ツイートの取得に失敗しました。",
                    "ERROR",
                )
        return []
