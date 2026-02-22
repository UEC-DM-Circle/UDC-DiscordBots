from common import *


class PDFmakerError(Exception):
    def __init__(self, message=""):
        self.message = message
