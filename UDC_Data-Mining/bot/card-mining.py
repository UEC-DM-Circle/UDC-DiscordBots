import discord
from discord.ext import commands
import os
from ability import cards

TOKEN =  os.getenv("TOKEN")
intent = discord.Intents.default()
intent.message_content= True

client = commands.Bot(
    command_prefix='_',
    intents=intent
)

# ここを変更していく
@client.command
async def test(message):
    await message.channel.send("The bot is working!")

@client.command
async def mining(ctx,query: str):
    await ctx.send("Mining...")
    queries=query.split()
    result=[]
    for q in queries:
        temp=[]
        for card in cards:
            for ability in cards[card]:
                if q in ability:
                    temp.append(card)
        new_result=[]
        if result != []:
            for t in temp:
                if t in result:
                    new_result.append(t)
            result=new_result
        else:
            result=temp
    result=list(set(result))
    message=""
    for i in range(len(result)):
        if result[i]!="":
            if i!=len(result)-1:
                message+=result[i]+"\n"
    if message=="":
        message="No result."
    await ctx.send("Completed!\n\n"+message)

client.run(TOKEN)