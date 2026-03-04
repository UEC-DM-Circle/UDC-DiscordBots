from common import *
from use_mysql import UseMySQL

intent = discord.Intents.default()
intent.message_content = True
client = commands.Bot(command_prefix="-", intents=intent)


async def check_channel(ctx):
    if ctx.channel.id in [CHANNEL_ID, TEST_CHANNEL_ID]:
        return True
    else:
        return False


@client.command()
async def test(ctx):
    if await check_channel(ctx):
        await ctx.send("Card-Recruitment Bot is Working!")


@client.command()
async def guide(ctx):
    if await check_channel(ctx):
        await ctx.send(
            "```"
            "【使い方を表示】\n"
            "-guide\n"
            "【募集追加】\n"
            "-want [カード名] [枚数]\n"
            "-want [人] [カード名] [枚数]\n"
            "※既存のカード名を指定した場合枚数が更新されます。\n"
            "　人を指定しない場合は自分の名前が使用されます。\n"
            "　半角スペースを含むカード名を入力しないようにしてください。\n"
            "【募集確認】\n"
            "-check [カード名/人](個別確認)\n"
            "-check (引数なしで全体確認)\n"
            "【募集終了】\n"
            "※募集IDは複数指定可能です。\n"
            "-end [募集ID]\n"
            "-end [人] [募集ID]\n"
            "```"
        )


@client.command()
async def want(ctx, *, args):
    args = args.split()
    # 追加している人が入力者本人かどうかでメッセージを変更する
    if await check_channel(ctx):
        arg_length = len(args)
        if arg_length in [2, 3]:
            if arg_length == 2:
                person = ctx.author.display_name
                card = args[0]
                num = args[1]
            else:
                person = args[0]
                card = args[1]
                num = args[2]
            if num.isdecimal():
                num = int(num)
                use_id_flag = False
                if card.isdecimal():
                    use_id_flag = True
                    card = int(card)
                    recruitments = await UseMySQL.run_sql(
                        "SELECT id, person, card, num, active FROM recruitments WHERE person = %s AND id = %s",
                        (person, card),
                    )
                else:
                    recruitments = await UseMySQL.run_sql(
                        "SELECT id, person, card, num, active FROM recruitments WHERE person = %s AND card = %s",
                        (person, card),
                    )
                if recruitments != []:
                    id = recruitments[0][0]
                    card_name = recruitments[0][2]
                    current_num = recruitments[0][3]
                    active = recruitments[0][4]
                    if active == 1:
                        if current_num == num:
                            await ctx.send(
                                f"**{person}**さんは既にその内容の募集(ID: {id})を行っています。"
                            )
                            return
                        else:
                            if use_id_flag:
                                await UseMySQL.run_sql(
                                    "UPDATE recruitments SET num = %s WHERE person = %s AND id = %s",
                                    (num, person, card),
                                )
                            else:
                                await UseMySQL.run_sql(
                                    "UPDATE recruitments SET num = %s WHERE person = %s AND card = %s",
                                    (num, person, card),
                                )
                            await ctx.send(
                                f"**{person}**さんの『{card_name}』の募集枚数を更新しました：\n×{current_num} → ×{num}"
                            )
                            return
                    else:
                        await UseMySQL.run_sql(
                            "UPDATE recruitments SET active = 1, num = %s WHERE person = %s AND card = %s",
                            (num, person, card),
                        )
                        await ctx.send(
                            f"**{person}**さんの募集を受け付けました：\n{card} ×{num}"
                        )
                        return
                else:
                    # 新規追加
                    await UseMySQL.run_sql(
                        "INSERT INTO recruitments (person, card, num) VALUES (%s, %s, %s)",
                        (person, card, num),
                    )
                    await ctx.send(
                        f"**{person}**さんの募集を受け付けました：\n{card} ×{num}"
                    )
                    return
        await ctx.send("募集追加方法に誤りがあります。")


@client.command()
async def check(ctx, *args):
    if await check_channel(ctx):
        recruitments = await UseMySQL.run_sql(
            "SELECT id, person, card, num FROM recruitments WHERE active = 1",
            (),
        )
        if recruitments == []:
            await ctx.send("現在進行中の募集はありません。")
            return
        else:
            # 全募集を確認
            text = ""
            arg_length = len(args)
            if arg_length == 0:
                people = set()
                for recruitment in recruitments:
                    people.add(recruitment[1])
                people = sorted(people)
                for person in people:
                    buffa = []
                    for recruitment in recruitments:
                        if recruitment[1] == person:
                            buffa.append(
                                (recruitment[0], f"{recruitment[2]} ×{recruitment[3]}")
                            )
                    buffa = sorted(buffa, key=lambda x: x[0])
                    text += f"**{person}**さんの募集一覧\n"
                    for item in buffa:
                        text += f"・{item[0]}：{item[1]}\n"
                    text += "\n"
                await ctx.send(text[:-2])
                return
            elif arg_length == 1:
                # 特定の人の募集を確認
                buffa = []
                person = args[0]
                for recruitment in recruitments:
                    if recruitment[1] == person:
                        buffa.append(
                            (recruitment[0], f"{recruitment[2]} ×{recruitment[3]}")
                        )
                if buffa != []:
                    buffa = sorted(buffa, key=lambda x: x[0])
                    text += f"**{person}**さんの募集一覧\n"
                    for item in buffa:
                        text += f"・{item[0]}：{item[1]}\n"
                    await ctx.send(text[:-1])
                    return
                # 特定のカードの募集を確認
                card = args[0]
                for recruitment in recruitments:
                    if recruitment[2] == card:
                        buffa.append(
                            (recruitment[0], f"×{recruitment[3]} by. {recruitment[1]}")
                        )
                if buffa != []:
                    buffa = sorted(buffa, key=lambda x: x[0])
                    text += f"『{card}』への募集一覧\n"
                    for item in buffa:
                        text += f"・{item[0]}：{item[1]}\n"
                    await ctx.send(text[:-1])
                    return
                await ctx.send("検索条件に該当する募集はありません。")
                return
            else:
                await ctx.send("募集確認方法に誤りがあります。")
                return


@client.command()
async def end(ctx, *, args):
    args = args.split()
    if await check_channel(ctx):
        arg_length = len(args)
        if arg_length > 0:
            if args[0].isdecimal():
                person = ctx.author.display_name
            else:
                person = args[0]
                args = args[1:]
            recruitments = await UseMySQL.run_sql(
                "SELECT id FROM recruitments WHERE person = %s AND active = 1",
                (person,),
            )
            if recruitments == []:
                await ctx.send(f"**{person}**さんが募集しているカードはありません。")
                return
            for arg in args:
                if not arg.isdecimal():
                    await ctx.send("募集IDを数字で指定してください。")
                    return
            ended_recruitments = []
            for arg in args:
                key = int(arg)
                recruitment = await UseMySQL.run_sql(
                    "SELECT id, card FROM recruitments WHERE person = %s AND id = %s AND active = 1",
                    (person, key),
                )
                if not recruitment:
                    ended_recruitments.append((key, ""))
                    continue
                card_name = recruitment[0][1]
                await UseMySQL.run_sql(
                    "UPDATE recruitments SET active = 0 WHERE id = %s",
                    (key,),
                )
                ended_recruitments.append((key, card_name))
            message_to_send = ""
            if len(ended_recruitments) == 1:
                key = ended_recruitments[0][0]
                card_name = ended_recruitments[0][1]
                if not card_name:
                    message_to_send += f"**{person}**さんの募集の中に指定されたID({key})のものはありませんでした。\n"
                else:
                    if person == ctx.author.display_name:
                        message_to_send += f"**{person}**さんが『{card_name}』の募集(ID: {key})を終了しました。\n"
                    else:
                        message_to_send += f"**{ctx.author.display_name}**さんが**{person}**さんの募集(ID: {key})を終了しました。\n"
            else:
                if person == ctx.author.display_name:
                    message_to_send += (
                        f"**{person}**さんが以下の募集を終了しました。\n\n"
                    )
                else:
                    message_to_send += f"**{ctx.author.display_name}**さんが**{person}**さんの以下の募集を終了しました。\n\n"
                for ended_recruitment in ended_recruitments:
                    key = ended_recruitment[0]
                    card_name = ended_recruitment[1]
                    if not card_name:
                        message_to_send += f"・該当なし (ID: {key})\n"
                    else:
                        message_to_send += f"・『{card_name}』(ID: {key})\n"
            await ctx.send(message_to_send[:-1])
            return
        else:
            await ctx.send("募集終了方法に誤りがあります。")
            return


client.run(TOKEN)
