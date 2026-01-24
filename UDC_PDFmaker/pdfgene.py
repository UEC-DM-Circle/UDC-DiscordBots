from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.utils import ImageReader
import requests, os, cv2, numpy as np
from PIL import Image
from io import BytesIO
import requests
from urllib.parse import urlparse, parse_qs
from glob import glob

margin = 0
margin_tp = 10
pics_folder_path = "./pics"
pdf_name = "artifact.pdf"
CARDHIGHT = 88
CARDWIDTH = 63
card_h = CARDHIGHT
card_w = CARDWIDTH
comp_ratio = 100
API_BASE_URL = "https://ockvhiwjud.execute-api.ap-northeast-1.amazonaws.com/prod/proxy/dm-decks/public/"
IMAGE_BASE_URL = "https://storage.googleapis.com/ka-nabell-card-images/img/card/"



def height(i):
    n = i // 3 + 1
    return 297 - margin_tp - (n * (card_h + margin))


def width(i):
    n = i % 3
    return margin_tp + (n * card_w)


def getHFromW(w):
    return CARDWIDTH * w / CARDHIGHT


def getWFromH(h):
    return CARDHIGHT * h / CARDWIDTH


def byte2cv2img(byte_data):
    nparr = np.frombuffer(byte_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def cv2img2pil(cv_img):
    rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb_img)
    return pil_img


def compress_image(pil_img, quality=comp_ratio):
    buffer = BytesIO()
    pil_img.save(buffer, format="JPEG", quality=quality, optimize=True)
    buffer.seek(0)
    return ImageReader(buffer)


def crop(image):  # 引数は画像の相対パス
    # 画像の読み込み
    img = byte2cv2img(image)

    # Grayscale に変換
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 色空間を二値化
    img2 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1]

    # 輪郭を抽出
    contours = cv2.findContours(img2, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]

    # 輪郭の座標をリストに代入していく
    x1 = []  # x座標の最小値
    y1 = []  # y座標の最小値
    x2 = []  # x座標の最大値
    y2 = []  # y座標の最大値
    for i in range(
        1, len(contours)
    ):  # i = 1 は画像全体の外枠になるのでカウントに入れない
        ret = cv2.boundingRect(contours[i])
        x1.append(ret[0])
        y1.append(ret[1])
        x2.append(ret[0] + ret[2])
        y2.append(ret[1] + ret[3])

    # 輪郭の一番外枠を切り抜き
    x1_min = min(x1)
    y1_min = min(y1)
    x2_max = max(x2)
    y2_max = max(y2)

    cropped_img = img[y1_min:y2_max, x1_min:x2_max]
    return cv2img2pil(cropped_img)

def getDeckId(url) -> str | None:
    """URLからデッキIDを取得する"""
    try:
        query = urlparse(url).query
        params = parse_qs(query)
        return params.get('tcgrevo_deck_maker_deck_id', [None])[0]
    except Exception:
        return None

def getJsonData(deck_id) -> dict | None:
    """デッキIDからデッキデータを取得する"""
    api_url = f"{API_BASE_URL}{deck_id}"
    try:
        res = requests.get(api_url, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception:
        return None

def getImageUrl(id_url: str) -> str:
    """カードIDから画像URLを取得する"""
    return IMAGE_BASE_URL + id_url

def getImageUrlsFromJson(card_infos: list) -> list[str]:
    """デッキデータから画像URLリストを取得する"""
    card_urls = []
    for card in card_infos:
        img_url = card.get("large_image_url")
        if img_url:
            card_urls.append(getImageUrl(img_url))
    return card_urls

def getImageUrlList(deck_url: str) -> tuple | None:
    """デッキURLから画像URLリストを取得する"""
    deck_id = getDeckId(deck_url)
    if not deck_id:
        return None
    data = getJsonData(deck_id)
    if not data:
        return None
    main_cards = data.get("dmDeck", {}).get("main_cards", [])
    gr_cards = data.get("dmDeck", {}).get("gr_cards", [])
    extra_cards = data.get("dmDeck", {}).get("hyper_spatial_cards", [])
    if not main_cards:
        return None
    return getImageUrlsFromJson(main_cards), getImageUrlsFromJson(gr_cards), getImageUrlsFromJson(extra_cards)

def make_pdf_from_images(image_urls: list):
    page = canvas.Canvas(pdf_name, pagesize=portrait(A4))

    for i in range(0, len(image_urls), 9):
        for j in range(9):
            if i + j < len(image_urls):
                page.drawImage(image_urls[i + j], width(j) * mm, height(j) * mm, card_w * mm, card_h * mm)
            page.showPage()
    
    return page

def pdfgene(url):
    #画像URLリストの取得    
    print("get image urls")
    main_cards, gr_cards, extra_cards = getImageUrlList(url)
    adextra_cards = []
    for card in extra_cards:
        for i in range(1,4):
            adextra_cards.append(card.split("_")[0] + "_" + str(i+1) + ".jpg")
    srcs = main_cards + gr_cards + extra_cards + adextra_cards

    #画像のダウンロード
    print("download images")
    imgs = []
    for src in srcs:
        r = requests.get(src)
        if r.status_code == 200:
            cropped_img = crop(r.content)
            imgs.append(compress_image(cropped_img))

    #pdf作成と画像追加
    print("make pdf")

    page = make_pdf_from_images(imgs)
    page.save()
    print("complete")


def rmpdf():
    pdf_files = glob(os.path.join("*.pdf"))
    for file in pdf_files:
        try:
            os.remove(file)
        except Exception as e:
            pass