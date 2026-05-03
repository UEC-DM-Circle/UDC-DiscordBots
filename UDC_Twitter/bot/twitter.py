from common import *
from crawler import Crawler
from use_mysql import UseMySQL

intent = discord.Intents.default()
intent.message_content = True
client = commands.Bot(command_prefix="*", intents=intent)
task = None


class Twitter:
    @staticmethod
    async def judge_issent(tweet_id: str) -> bool:
        return (
            await UseMySQL.run_sql(
                "SELECT id FROM tweets WHERE tweet_id = %s", (tweet_id,)
            )
            != []
        )

    @classmethod
    async def send_tweet(cls, tweet: dict):
        tweet_text = tweet["text"]
        tweet_id = tweet["id"]
        tweet_url = f"https://x.com/{TWITTER_USER_ID}/status/{tweet_id}"
        is_retweet = tweet_text.startswith("RT @")
        if await cls.judge_issent(tweet_id):
            return
        channel = client.get_channel(CHANNEL_ID)
        await channel.send(f"新しい投稿です！拡散よろしくお願いします！\n{tweet_url}")
        await UseMySQL.run_sql(
            "INSERT INTO tweets (text, tweet_id, url, is_retweet) VALUES (%s, %s, %s, %s)",
            (tweet_text, tweet_id, tweet_url, is_retweet),
        )


async def main():
    while True:
        try:
            if await Crawler.check_latest_api_crawl_time():
                latest_tweets = reversed(
                    await Crawler.fetch_latest_tweets(GET_TWEET_NUMBER)
                )
                for latest_tweet in latest_tweets:
                    await Twitter.send_tweet(latest_tweet)
                    # Discord側でプレビューが開くように少し待つ
                    await asyncio.sleep(3)
        except Exception as e:
            await write_log_message(f"{e}", "ERROR")
            traceback.print_exc()
        # 15分ごとにクロール
        await asyncio.sleep(15 * 60)


@client.event
async def test(ctx):
    if ctx.channel.id == CHANNEL_ID:
        await ctx.channel.send("Twitter Bot is Working!")


@client.event
async def on_ready():
    global task
    await UseMySQL.init_pool()
    await Crawler.init_session()
    await write_log_message("Bot is ready!", "INFO")
    if task is None or task.done():
        task = asyncio.create_task(main())


client.run(TOKEN)
