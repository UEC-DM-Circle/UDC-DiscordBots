from common import *
from use_mysql import UseMySQL


class Want:
    async def parse_args(args: list) -> str:
        arg_length = len(args)
