from common import *
from use_mysql import UseMySQL


# 以下のメソッドを作る
# 送るメッセージを作成する
# SQLを実行する
class Want:
    async def parse_args(ctx: commands.Context, args: list) -> str:
        arg_length = len(args)
        if arg_length == 2:
            person = ctx.author.display_name
            card_name = args[0]
            num = args[1]
        else:
            person = args[0]
            card_name = args[1]
            num = args[2]
        # 解析結果に合わせてメソッドを分けようぜ
        if num.isdecimal():
            num = int(num)
            if card_name.isdecimal():
                card_id = int(card_name)
                recruitments = await UseMySQL.run_sql(
                    "SELECT id, person, card, num, active FROM recruitments WHERE person = %s AND id = %s",
                    (person, card_id),
                )
            else:
                recruitments = await UseMySQL.run_sql(
                    "SELECT id, person, card, num, active FROM recruitments WHERE person = %s AND card = %s",
                    (person, card_name),
                )

    async def use_id():
        pass
