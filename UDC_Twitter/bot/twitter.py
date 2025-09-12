import discord
from discord.ext import commands
import mysql.connector
import requests
import asyncio
import os
import traceback

TOKEN = os.getenv("TOKEN")
intent = discord.Intents.default()
intent.message_content = True
client = commands.Bot(command_prefix="*", intents=intent)
channel_id = int(os.environ.get("CHANNEL_ID"))
user_name = os.getenv("TWITTER_USER_NAME")


def is_correct_channel(ctx):
    return ctx.channel.id == channel_id


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


async def run_sql(sql: str, params: tuple):
    conn = get_connection()
    cursor = conn.cursor(buffered=True)
    if params != ():
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    if sql.strip().upper().startswith("SELECT"):
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result
    else:
        conn.commit()
        cursor.close()
        conn.close()
        return


async def fetch_latest_tweets(max_results: int):
    retries = 5
    bearer_token = os.getenv("BEARER_TOKEN")
    user_id = os.getenv("TWITTER_USER_ID")
    if not user_id:
        return []
    url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "User-Agent": "v2UserTweetsPython",
    }
    params = {"max_results": max_results, "tweet.fields": "text,public_metrics"}
    for attempt in range(retries):
        await asyncio.sleep(1)
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json().get("data", [])
        elif response.status_code == 429:
            print(f"レート制限に到達しました。")
            await asyncio.sleep(200 * (attempt + 1))
        else:
            print(f"エラー: {response.status_code}, {response.text}")
    return []


async def main():
    get_tweet_number = 5
    latest_tweets = reversed(await fetch_latest_tweets(get_tweet_number))
    if not latest_tweets:
        return
    for tweet in latest_tweets:
        public_metrics = tweet["public_metrics"]
        tweet_text = tweet["text"]
        tweet_id = tweet["id"]
        tweet_url = f"https://x.com/{user_name}/status/{tweet_id}"
        is_retweet = tweet_text.startswith("RT @")
        existing = await run_sql(
            "SELECT id FROM tweets WHERE tweet_id = %s", (tweet_id,)
        )
        if existing:
            continue
        channel = client.get_channel(channel_id)
        await channel.send(f"新しい投稿です！拡散よろしくお願いします！\n{tweet_url}")
        await run_sql(
            "INSERT INTO tweets (text, tweet_id, url, is_retweet) VALUES (%s, %s, %s, %s)",
            (tweet_text, tweet_id, tweet_url, is_retweet),
        )
        await run_sql(
            "INSERT INTO public_metrics (tweet_id, retweet_count, reply_count, like_count, quote_count) VALUES (%s, %s, %s, %s, %s)",
            (
                tweet_id,
                public_metrics["retweet_count"],
                public_metrics["reply_count"],
                public_metrics["like_count"],
                public_metrics["quote_count"],
            ),
        )
    return


@client.event
async def test(ctx):
    if is_correct_channel(ctx):
        await ctx.channel.send("Twitter Bot is Working!")


@client.event
async def on_ready():
    print("Bot is ready!")
    while True:
        try:
            await main()
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
        await asyncio.sleep(1000)


client.run(TOKEN)
