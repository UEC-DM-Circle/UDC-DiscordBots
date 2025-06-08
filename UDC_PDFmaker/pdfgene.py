from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.utils import ImageReader
import time, requests, os, cv2, re, numpy as np
from PIL import Image
from io import BytesIO
from glob import glob

margin = 0
margin_tp = 15
pics_folder_path = './pics'
pdf_name = "artifact.pdf"
CARDHIGHT = 88
CARDWIDTH = 63
card_h = CARDHIGHT
card_w = CARDWIDTH
comp_ratio = 70

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

def crop(image): #引数は画像の相対パス
  # 画像の読み込み
  img = byte2cv2img(image)

  # Grayscale に変換
  gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

  # 色空間を二値化
  img2 = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1]

  # 輪郭を抽出
  contours = cv2.findContours(img2, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]

  # 輪郭の座標をリストに代入していく
  x1 = [] #x座標の最小値
  y1 = [] #y座標の最小値
  x2 = [] #x座標の最大値
  y2 = [] #y座標の最大値
  for i in range(1, len(contours)):# i = 1 は画像全体の外枠になるのでカウントに入れない
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

def pdfgene(url):
  print('start')

  #chromeドライバの設定
  chrome_options = Options()
  chrome_options.add_argument('--no-sandbox')
  chrome_options.add_argument('--disable-dev-shm-usage')
  chrome_options.add_argument('--headless=new')
  driver = webdriver.Chrome(options=chrome_options)

  #デッキページにアクセス
  print("access url")
  driver.get(url)
  time.sleep(0.5)
  print("get image urls")
  imgs = driver.find_elements(By.CLASS_NAME, 'item8_img')
  srcs = []
  for img in imgs:
    if re.match("chojigen_.", img.get_attribute("alt")):
      for i in range(4):
        srcs.append(img.get_attribute("src").split("_")[0] + "_" + str(i+1) + ".jpg")
    else:
      srcs.append(img.get_attribute("src"))
  driver.quit()

  #画像のダウンロード
  print("download images")
  imgs = []
  for src in srcs:
    page = src.replace('/img/s/', '/img/')
    r = requests.get(page)
    if r.status_code == 200:
      cropped_img = crop(r.content)
      imgs.append(compress_image(cropped_img))

  #pdf作成と画像追加
  print("make pdf")
  page = canvas.Canvas(pdf_name, pagesize=portrait(A4))

  for i in range(0, len(imgs), 9):
    for j in range(9):
      if i + j < len(imgs):
        page.drawImage(imgs[i + j], width(j) * mm, height(j) * mm, card_w * mm, card_h * mm)
    page.showPage()

  page.save()
  print("complete")

def rmpdf():
  pdf_files = glob(os.path.join('*.pdf'))
  for file in pdf_files:
    try:
      os.remove(file)
    except Exception as e:
      pass