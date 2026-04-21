from common import *
from use_mysql import UseMySQL
from logic import Logic


class Crawler:
    session: aiohttp.ClientSession | None = None

    @classmethod
    async def init_session(cls):
        if cls.session is None:
            connector = aiohttp.TCPConnector(family=socket.AF_INET)
            timeout = aiohttp.ClientTimeout(total=30)
            cls.session = aiohttp.ClientSession(timeout=timeout, connector=connector)

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
        except aiohttp.client_exceptions.ClientConnectorError:
            # DNSエラーや接続拒否など、リトライしても無駄なネットワークエラーは即終了
            return "FATAL_ERROR"
        except Exception as e:
            print(f"Exception: {type(e).__name__} - {e}")
            return "ERROR"

    @classmethod
    async def try_to_get_image_size(cls, url: str, retries: int = 5) -> tuple:
        for _ in range(retries):
            size = await cls.get_image_size(url)
            if size == "FATAL_ERROR":
                break
            if size != "ERROR":
                return size
        # サイズが見つからない場合は(0, 0)を返す
        return (0, 0)

    @classmethod
    async def get_soup(cls, url: str) -> BeautifulSoup | str:
        try:
            await asyncio.sleep(1)
            async with cls.session.get(url) as resp:
                if resp.status != 200:
                    return "ERROR"
                text = await resp.text()
                return BeautifulSoup(text, "html.parser")
        except Exception as e:
            print(f"Exception: {type(e).__name__} - {e}")
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
    async def get_title(cls, url: str) -> str:
        soup = await cls.try_to_get_soup(url)
        if soup == "FAILED":
            return ""
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.text.strip()
        return ""

    @classmethod
    async def get_new_denen_articles(cls) -> list:
        soup = await cls.try_to_get_soup(DENEN_URL)
        if soup == "FAILED":
            return []
        await cls.register_crawl(DENEN_URL, "HTTP_GET")
        titles = soup.find_all("div", class_="EntryTitle")
        new_articles = []
        for div in titles:
            a = div.find("a")
            if not a:
                continue
            url = a.get("href")
            title = div.text.strip()
            category = await Logic.judge_denen_category(title)
            new_articles.append({"url": url, "title": title, "category": category})
        return new_articles

    @classmethod
    async def get_new_deneblog_articles(cls) -> list:
        soup = await cls.try_to_get_soup(DENEBLOG_URL)
        if soup == "FAILED":
            return []
        await cls.register_crawl(DENEBLOG_URL, "HTTP_GET")
        main_div = soup.find("div", id="main")
        titles = main_div.find_all("h1", class_="ently_title")
        new_articles = []
        for title in titles:
            a = title.find("a")
            if not a:
                continue
            url = a.get("href")
            title_text = title.text.strip()
            category = await Logic.judge_deneblog_category(title_text)
            new_articles.append({"url": url, "title": title_text, "category": category})
        return new_articles
