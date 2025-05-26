from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
import re
import os
import cv2
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4, portrait
import glob
import numpy as np
from PIL import Image

margin = 0
margin_tp = 15
pdf_name="artifact.pdf"
pics_folder_path = './pics'
CARDHIGHT = 88
CARDWIDTH = 63
card_h = CARDHIGHT
card_w = CARDWIDTH

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

def crop(image_bytes): #引数はbyte画像
  # 画像の読み込み
  nparr = np.frombuffer(image_bytes, np.uint8)
  img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
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
  rgb = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB)
  pil_img = Image.fromarray(rgb)

  return pil_img

def pdfgene(url):
  print('start')
  service = Service(ChromeDriverManager().install())
  chrome_options = Options()
  chrome_options.add_argument('--no-sandbox')
  chrome_options.add_argument('--disable-dev-shm-usage')
  chrome_options.add_argument('--headless')
  chrome_options.add_argument('--no-proxy-server')
  driver = webdriver.Chrome(service=service, options=chrome_options)
  driver.get(url)
  time.sleep(0.5)
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
  count = 0
  download_imgs = []
  for src in srcs:
    page = src.replace('/img/s/', '/img/')
    r = requests.get(page)
    count += 1
    if r.status_code == 200:
      download_imgs.append(r.content)
  #pdf作成と画像追加
  page = canvas.Canvas(pdf_name, pagesize=portrait(A4))

  croped_imgs = [ crop(dimg) for dimg in download_imgs]
  for i in range(0, len(croped_imgs), 9):
    for j in range(9):
      if i + j < len(croped_imgs):
        page.drawInlineImage(croped_imgs[i + j], width(j) * mm, height(j) * mm, card_w * mm, card_h * mm)
    page.showPage()
  page.save()
  print("complete")

def rmpdf():
  pdf_files = glob.glob(os.path.join('*.pdf'))
  for file in pdf_files:
    try:
      os.remove(file)
    except Exception as e:
      pass