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
