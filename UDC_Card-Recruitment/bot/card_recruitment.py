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


async def retrieve_udc_member_id(name: str) -> str:
    udc_member_id = await UseMySQL.run_sql(
        "SELECT id FROM udc_members WHERE name = %s", (name,)
    )
    if udc_member_id == []:
        # 新規登録
        await UseMySQL.run_sql("INSERT INTO udc_members (name) VALUES (%s)", (name,))
        udc_member_id = await UseMySQL.run_sql(
            "SELECT id FROM udc_members WHERE name = %s", (name,)
        )
    return udc_member_id[0][0]


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
            "\n"
            "【募集追加】\n"
            "-want [カード名/ID] [枚数]\n"
            "※既存のカード名またはIDを指定した場合枚数が更新されます。\n"
            "　枚数を指定しない場合は1枚として扱われます。\n"
            "　カード名の末尾が空白+数字となっているもの(偽りの名 13など)の募集の際には区別のため枚数を明示してください。\n"
            "\n"
            "【募集確認】\n"
            "-check [カード名/人](個別確認)\n"
            "-check (引数なしで全体確認)\n"
            "\n"
            "【募集終了】\n"
            "-end [募集ID]\n"
            "-end [人] [募集ID]\n"
            "※募集IDは複数指定可能です。\n"
            "-end [募集ID1] [募集ID2] ...\n"
            "-end [人] [募集ID1] [募集ID2] ...\n"
            "```"
        )


@client.command()
async def want(ctx, *, args):
    args = args.split()
    name = ctx.author.display_name
    udc_member_id = await retrieve_udc_member_id(name)
    if await check_channel(ctx):
        arg_length = len(args)
        if arg_length >= 1:
            if args[-1].isdecimal():
                num = args[-1]
                args = args[:-1]
            else:
                num = "1"
            card = " ".join(args)
            num = int(num)
            use_id_flag = False
            if card.isdecimal():
                use_id_flag = True
                card = int(card)
                recruitments = await UseMySQL.run_sql(
                    "SELECT id, udc_member_id, card, num, active FROM recruitments WHERE udc_member_id = %s AND id = %s",
                    (udc_member_id, card),
                )
            else:
                recruitments = await UseMySQL.run_sql(
                    "SELECT id, udc_member_id, card, num, active FROM recruitments WHERE udc_member_id = %s AND card = %s",
                    (udc_member_id, card),
                )
            if recruitments != []:
                id = recruitments[0][0]
                card_name = recruitments[0][2]
                current_num = recruitments[0][3]
                active = recruitments[0][4]
                if active == 1:
                    if current_num == num:
                        await ctx.send(
                            f"**{name}**さんは既にその内容の募集(ID: {id})を行っています。"
                        )
                        return
                    else:
                        if use_id_flag:
                            await UseMySQL.run_sql(
                                "UPDATE recruitments SET num = %s WHERE udc_member_id = %s AND id = %s",
                                (num, udc_member_id, card),
                            )
                        else:
                            await UseMySQL.run_sql(
                                "UPDATE recruitments SET num = %s WHERE udc_member_id = %s AND card = %s",
                                (num, udc_member_id, card),
                            )
                        await ctx.send(
                            f"**{name}**さんの『{card_name}』の募集枚数を更新しました：\n×{current_num} → ×{num}"
                        )
                        return
                else:
                    await UseMySQL.run_sql(
                        "UPDATE recruitments SET active = 1, num = %s WHERE udc_member_id = %s AND card = %s",
                        (num, udc_member_id, card),
                    )
                    await ctx.send(
                        f"**{name}**さんの募集を受け付けました：\n『{card}』×{num}"
                    )
                    return
            else:
                # 新規追加
                await UseMySQL.run_sql(
                    "INSERT INTO recruitments (udc_member_id, card, num) VALUES (%s, %s, %s)",
                    (udc_member_id, card, num),
                )
                await ctx.send(
                    f"**{name}**さんの募集を受け付けました：\n『{card}』×{num}"
                )
                return
        await ctx.send("募集追加方法に誤りがあります。")


@client.command()
async def check(ctx, *args):
    if await check_channel(ctx):
        recruitments = await UseMySQL.run_sql(
            "SELECT r.id, name, card, num FROM recruitments r JOIN udc_members um ON um.id = r.udc_member_id WHERE active = 1",
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
                for name in people:
                    buffa = []
                    for recruitment in recruitments:
                        if recruitment[1] == name:
                            buffa.append(
                                (recruitment[0], f"{recruitment[2]} ×{recruitment[3]}")
                            )
                    buffa = sorted(buffa, key=lambda x: x[0])
                    text += f"**{name}**さんの募集一覧\n"
                    for item in buffa:
                        text += f"・{item[0]}：{item[1]}\n"
                    text += "\n"
                await ctx.send(text[:-2])
                return
            elif arg_length == 1:
                # 特定の人の募集を確認
                buffa = []
                name = args[0]
                for recruitment in recruitments:
                    if recruitment[1] == name:
                        buffa.append(
                            (recruitment[0], f"{recruitment[2]} ×{recruitment[3]}")
                        )
                if buffa != []:
                    buffa = sorted(buffa, key=lambda x: x[0])
                    text += f"**{name}**さんの募集一覧\n"
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
            people = await UseMySQL.run_sql(
                "SELECT DISTINCT name FROM recruitments r JOIN udc_members um ON um.id = r.udc_member_id WHERE active = 1",
                (),
            )
            people = sorted([name[0] for name in people])
            if args[0] in people or not args[0].isdecimal():
                if arg_length == 1:
                    if args[0].isdecimal():
                        key = int(args[0])
                        name = ctx.author.display_name
                        udc_member_id = await retrieve_udc_member_id(name)
                        reqruitment = await UseMySQL.run_sql(
                            "SELECT id, card FROM recruitments WHERE active = 1 AND id = %s AND udc_member_id = %s",
                            (key, udc_member_id),
                        )
                        if reqruitment == []:
                            await ctx.send(
                                f"**{name}**さんの募集の中に指定されたID({key})のものはありませんでした。"
                            )
                            return
                    else:
                        await ctx.send("募集IDを数字で指定してください。")
                        return
                else:
                    name = args[0]
                    args = args[1:]
            else:
                name = ctx.author.display_name
            udc_member_id = await retrieve_udc_member_id(name)
            recruitments = await UseMySQL.run_sql(
                "SELECT id FROM recruitments WHERE udc_member_id = %s AND active = 1",
                (udc_member_id,),
            )
            if recruitments == []:
                await ctx.send(f"**{name}**さんが募集しているカードはありません。")
                return
            for arg in args:
                if not arg.isdecimal():
                    await ctx.send("募集IDを数字で指定してください。")
                    return
            ended_recruitments = []
            for arg in args:
                key = int(arg)
                recruitment = await UseMySQL.run_sql(
                    "SELECT id, card FROM recruitments WHERE udc_member_id = %s AND id = %s AND active = 1",
                    (udc_member_id, key),
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
                    message_to_send += f"**{name}**さんの募集の中に指定されたID({key})のものはありませんでした。\n"
                else:
                    if name == ctx.author.display_name:
                        message_to_send += f"**{name}**さんが『{card_name}』の募集(ID: {key})を終了しました。\n"
                    else:
                        message_to_send += f"**{ctx.author.display_name}**さんが**{name}**さんの募集(ID: {key})を終了しました。\n"
            else:
                if name == ctx.author.display_name:
                    message_to_send += f"**{name}**さんが以下の募集を終了しました。\n\n"
                else:
                    message_to_send += f"**{ctx.author.display_name}**さんが**{name}**さんの以下の募集を終了しました。\n\n"
                any_recruiment_ended = False
                for ended_recruitment in ended_recruitments:
                    key = ended_recruitment[0]
                    card_name = ended_recruitment[1]
                    if not card_name:
                        message_to_send += f"・該当なし (ID: {key})\n"
                    else:
                        any_recruiment_ended = True
                        message_to_send += f"・『{card_name}』(ID: {key})\n"
                if not any_recruiment_ended:
                    message_to_send = f"**{name}**さんの募集の中に指定されたIDのものは1つもありませんでした。\n"
            await ctx.send(message_to_send[:-1])
            return
        else:
            await ctx.send("募集終了方法に誤りがあります。")
            return


client.run(TOKEN)
