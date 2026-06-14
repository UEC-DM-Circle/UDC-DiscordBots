from common import *
from use_mysql import UseMySQL

# 定数
MARGIN = 0
MARGIN_TOP = 10
CARD_HEIGHT = 88
CARD_WIDTH = 63
COMP_RATIO = 100


def height(i: int) -> int:
    n = i // 3 + 1
    return 297 - MARGIN_TOP - (n * (CARD_HEIGHT + MARGIN))


def width(i: int) -> int:
    n = i % 3
    return MARGIN_TOP + (n * CARD_WIDTH)


def get_h_from_w(w: int) -> float:
    return CARD_WIDTH * w / CARD_HEIGHT


def get_w_from_h(h: int) -> float:
    return CARD_HEIGHT * h / CARD_WIDTH


def byte_to_cv2_img(byte_data: bytes) -> np.ndarray:
    nparr = np.frombuffer(byte_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img


def cv2_img_to_pil_img(cv2_img: np.ndarray) -> Image.Image:
    rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb_img)
    return pil_img


def compress_image(pil_img: Image.Image, quality: int = COMP_RATIO) -> ImageReader:
    buffer = BytesIO()
    pil_img.save(buffer, format="JPEG", quality=quality, optimize=True)
    buffer.seek(0)
    return ImageReader(buffer)


def crop_img(image: bytes) -> ImageReader:  # 引数は画像のバイトデータ
    # 画像の読み込み
    img = byte_to_cv2_img(image)
    # Grayscale に変換
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 色空間を二値化
    binary_img = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1]
    # 輪郭を抽出
    contours = cv2.findContours(binary_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]
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
    # 切り抜いた画像をPIL形式に変換して圧縮したものを返す
    cropped_img = img[y1_min:y2_max, x1_min:x2_max]
    pil_img = cv2_img_to_pil_img(cropped_img)
    return compress_image(pil_img)


def retrive_id(table_name: str, key: str):
    id = UseMySQL.run_sql(
        "SELECT id FROM {} WHERE name = %s".format(table_name), (key,)
    )
    if not id:
        return None
    return id[0][0]


def register_crawl(target_url: str, crawl_method: str):
    crawl_method_id = retrive_id("crawl_methods", crawl_method)
    service_id = retrive_id("services", SERVICE_NAME)
    if crawl_method_id is None or service_id is None:
        return
    UseMySQL.run_sql(
        "INSERT INTO crawls (target_url, crawl_method_id, service_id) VALUES (%s, %s, %s)",
        (
            target_url,
            crawl_method_id,
            service_id,
        ),
    )


def register_api_status_code(status_code: int, crawl_method: str):
    crawl_method_id = retrive_id("crawl_methods", crawl_method)
    service_id = retrive_id("services", SERVICE_NAME)
    if crawl_method_id is None or service_id is None:
        return
    latest_crawl_id = UseMySQL.run_sql(
        "SELECT id FROM crawls WHERE crawl_method_id = %s AND service_id = %s ORDER BY created_at DESC LIMIT 1",
        (crawl_method_id, service_id),
    )
    if not latest_crawl_id:
        return
    UseMySQL.run_sql(
        "INSERT INTO api_status_codes (crawl_id, status_code) VALUES (%s, %s)",
        (latest_crawl_id[0][0], status_code),
    )


async def get_deck_id(url: str) -> str | None:
    # URLからデッキIDを取得する
    try:
        query = urlparse(url).query
        params = parse_qs(query)
        return params.get("tcgrevo_deck_maker_deck_id", [None])[0]
    except Exception as e:
        await write_log_message("デッキIDの取得に失敗しました。", "ERROR")
        await write_log_message(f"{e}", "ERROR")
        return None


async def get_json_data(deck_id: str) -> dict | None:
    # デッキIDからデッキデータを取得する
    api_url = f"{API_BASE_URL}{deck_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        await asyncio.sleep(1)
        res = requests.get(api_url, headers=headers, timeout=10)
        register_crawl(api_url, "Amazon_API")
        register_api_status_code(res.status_code, "Amazon_API")
        res.raise_for_status()
        return res.json()
    except Exception as e:
        await write_log_message("デッキデータの取得に失敗しました。", "ERROR")
        await write_log_message(f"{e}", "ERROR")
        return None


def get_image_url(id_url: str) -> str:
    # カードIDから画像URLを取得する
    return IMAGE_BASE_URL + id_url


def get_image_urls_from_json(card_infos: list) -> list[str]:
    # デッキデータから画像URLリストを取得する
    card_urls = []
    for card in card_infos:
        img_url = card.get("large_image_url")
        if img_url:
            card_urls.append(get_image_url(img_url))
    return card_urls


async def get_image_url_list(deck_url: str) -> tuple | None:
    # デッキURLから画像URLリストを取得する
    deck_id = await get_deck_id(deck_url)
    if not deck_id:
        return None, None, None
    data = await get_json_data(deck_id)
    if not data:
        return None, None, None
    main_cards = data.get("dmDeck", {}).get("main_cards", [])
    gr_cards = data.get("dmDeck", {}).get("gr_cards", [])
    extra_cards = data.get("dmDeck", {}).get("hyper_spatial_cards", [])
    if not main_cards:
        return None, None, None
    return (
        get_image_urls_from_json(main_cards),
        get_image_urls_from_json(gr_cards),
        get_image_urls_from_json(extra_cards),
    )


def make_pdf_binary_from_images(image_urls: list) -> BytesIO:
    buffer = BytesIO()
    page = canvas.Canvas(buffer, pagesize=portrait(A4))
    for i in range(0, len(image_urls), 9):
        for j in range(9):
            if i + j < len(image_urls):
                page.drawImage(
                    image_urls[i + j],
                    width(j) * mm,
                    height(j) * mm,
                    CARD_WIDTH * mm,
                    CARD_HEIGHT * mm,
                )
        page.showPage()
    page.save()
    buffer.seek(0)
    return buffer


async def generate_pdf_binary(url, ngr_option=False, nsp_option=False) -> BytesIO:
    try:
        # 画像URLリストの取得
        await write_log_message("画像URLを取得中...", "INFO")
        main_cards, gr_cards, extra_cards = await get_image_url_list(url)
        if main_cards is None:
            await write_log_message("画像URLの取得に失敗しました。", "ERROR")
            return None
        advance_extra_cards = []
        if not nsp_option:
            for card in extra_cards:
                for i in range(1, 4):
                    advance_extra_cards.append(
                        card.split("_")[0] + "_" + str(i + 1) + ".jpg"
                    )
        # オプションの適用
        srcs = main_cards
        if not ngr_option:
            srcs += gr_cards
        if not nsp_option:
            srcs += extra_cards
            srcs += advance_extra_cards
        # 画像のダウンロード
        await write_log_message("画像をダウンロード中...", "INFO")
        imgs = []
        for src in srcs:
            await asyncio.sleep(1)
            r = requests.get(src)
            if r.status_code == 200:
                imgs.append(crop_img(r.content))
                register_crawl(src, "HTTP_GET")
        # pdf作成と画像追加
        await write_log_message("PDFを生成中...", "INFO")
        page = make_pdf_binary_from_images(imgs)
        await write_log_message("PDFの生成に成功しました。", "INFO")
        return page
    except PDFmakerError as e:
        await write_log_message(f"{e}", "ERROR")
        return None
    except Exception as e:
        await write_log_message(f"{e}", "FATAL")
        return None
