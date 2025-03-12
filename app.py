from time import sleep
from bs4 import BeautifulSoup
import requests
import pandas as pd
import schedule
import time
import re
import os
from datetime import datetime

url = 'https://suumo.jp/jj/chintai/ichiran/FR301FC001/?ar=030&bs=040&pc=30&smk=&po1=25&po2=99&kz=1&kz=2&tc=0400104&shkr1=03&shkr2=03&shkr3=03&shkr4=03&rn=0220&ek=022039270&ek=022033150&ek=022005650&ek=022010720&ek=022038540&ek=022030290&ek=022040940&ra=014&cb=0.0&ct=7.5&co=1&md=02&md=03&md=04&ts=1&ts=2&et=15&mb=20&mt=9999999&cn=25&tc=0400301&tc=0400101&tc=0400501&tc=0400601&tc=0401106&fw2='

url_1 = url.format(1)
r_1 = requests.get(url_1)
soup_1 = BeautifulSoup(r_1.text, 'html.parser')

# 物件数の取得
house_num_text = soup_1.find('div', class_='paginate_set-hit').text
num = int(re.sub(r"\D", "", house_num_text))

# ページあたりの件数
num_per_page_select = soup_1.find("select", {"id": "js-tabmenu1-pcChange"})
selected_option = num_per_page_select.find("option", selected=True)
num_per_page = int(selected_option.get("value"))

d_list = []

# ページ数の計算
page = (num // num_per_page) + (1 if num % num_per_page != 0 else 0)
print(f"ページ数: {page}")

# ヘッダー偽装（ブラウザっぽくする）
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
}

# 築年数を文字列から抽出する関数
def extract_build_year(text):
    """
    築年数を文字列から抽出する関数
    例: '築37年3階建' -> 37
    """
    match = re.search(r'築(\d+)年', text)
    if match:
        return str('築') + str(match.group(1)) + str('年')
    else:
        return None  # 該当しない場合は None を返す

# 階数を文字列から抽出する関数
def extract_floor(text):
    match = re.search(r'(\d+)階', text)
    if match:
        return str(match.group(1)) + str('階')
    else:
        return None  # 該当しない場合は None を返す

# 物件データの抽出
for i in range(1, page + 1):
    target_url = url.format(i)
    print(f"スクレイピング中: {i} / {page}")
    sleep(2)
    res = requests.get(target_url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    contents = soup.find_all('div', class_='cassetteitem')

    # 各物件の情報を抽出
    for content in contents:
        # 物件名
        title_tag = content.find('div', class_='cassetteitem_content-title')
        title = title_tag.text.strip() if title_tag else 'N/A'
        # 駅・徒歩
        station_tag = content.find('li', class_='cassetteitem_detail-col2')
        station = station_tag.text.strip() if station_tag else 'N/A'
        # 築年数
        age_tag = content.find('li', class_='cassetteitem_detail-col3')
        age = age_tag.text.strip() if age_tag else 'N/A'
        age = extract_build_year(age)
        # 家賃
        rent_tag = content.find('span', class_='cassetteitem_price cassetteitem_price--rent')
        rent = rent_tag.text.strip() if rent_tag else 'N/A'
        # 管理費
        fee_tag = content.find('span', class_='cassetteitem_price cassetteitem_price--administration')
        fee = fee_tag.text.strip() if fee_tag else 'N/A'
        # 間取り
        madori_tag = content.find('span', class_='cassetteitem_madori')
        madori = madori_tag.text.strip() if madori_tag else 'N/A'
        if madori == 'ワンルーム':
            madori = '1R'
        else:
            madori = madori
        # 面積
        menseki_tag = content.find('span', class_='cassetteitem_menseki')
        menseki = menseki_tag.text.strip() if menseki_tag else 'N/A'
        # 階数
        kaisu_tag = content.find('tr', class_='js-cassette_link')
        kaisu = kaisu_tag.text.strip() if kaisu_tag else 'N/A'
        kaisu = extract_floor(kaisu)
        # 詳細ページURL
        link_tag = content.find('a', class_='js-cassette_link_href')
        link = 'https://suumo.jp' + link_tag.get('href') if link_tag else 'N/A'

        d_list.append({
            '物件名': title,
            #'駅・徒歩': station,
            '築年数': age,
            #'階数': kaisu,
            '家賃': rent,
            '管理費': fee,
            #'間取り': madori,
            '面積': menseki,
            'URL': link
        })

# LINE Messaging APIのチャネルアクセストークン
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
if LINE_ACCESS_TOKEN is None:
    print("環境変数 LINE_ACCESS_TOKEN が設定されていません")
else:
    print("アクセストークンが正常に取得できました")

def send_line_message(message):
    """LINEにメッセージを送る"""
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    import json
    data = {
        "messages": [
            {"type": "text", "text": message}]
    }
    response = requests.post(url, json=data, headers=headers)
    return response.status_code

# 各行をテキスト形式に変換
df_new = pd.DataFrame(d_list)
today_str = datetime.today().strftime('%Y%m%d')
filename = f"{today_str}_suumo.csv"
df_new.to_csv(filename, index=False)
print(f"新規データを {filename} に保存しました。")

# 1回前のデータと比較
prev_files = sorted([f for f in os.listdir() if f.endswith("_suumo.csv")])
if len(prev_files) > 1:
    prev_file = prev_files[-2]
    df_prev = pd.read_csv(prev_file)
    df_diff = df_new[~df_new['URL'].isin(df_prev['URL'])]

    if not df_diff.empty:
        diff_filename = f"{today_str}_suumo_new.csv"
        df_diff.to_csv(diff_filename, index=False)
        print(f"新規物件のみを {diff_filename} に保存しました。")
    else:
        print("新規物件はありません。")
else:
    print("比較用の過去データがありません。")

# 新規物件ファイルがある場合にのみ、物件を通知
if os.path.exists(f"{today_str}_suumo_new.csv"):
    print("新規物件情報があります。")
    df2 = pd.read_csv(f"{today_str}_suumo_new.csv")
    # 各行をテキスト形式に変換
    text = df2.to_string(index=False)

    # 結果をファイルに保存（オプション）
    with open("output.txt", "w", encoding="utf-8") as f:
        f.write(text)

    print(text)  # 確認用

    # 1. タブ（\t）、改行（\n, \r）をスペースに置換
    text = re.sub(r'[\t\n\r]+', ' ', text)
    text = text.replace("\\r", "")
    text = text.replace("\\t", "")
    text = text.replace("\\n", "")
    text = text.replace("\n", "")
    text = text.replace("\t", "")
    text = text.replace("\r", "")

    # 追加する文
    intro_text = "🏡新着物件情報のお知らせ🏡\nこんにちは！\n住まいコンシェルジュです✨\n今週のおすすめ物件をお届けします！\n"
    # textの最初に追加
    text = intro_text + text
    last_text="気になる物件がありましたら、お早めにお問い合わせください！😊\n次回の更新もお楽しみに✨"
    text = text + last_text
    # 2. 連続するスペースを1つに統一
    text = re.sub(r'\s+', ' ', text).strip()

    # LINE通知送信
    if len(text) > 500:
        messages = [text[i:i+500] for i in range(0, len(text), 500)]
        for msg in messages:
            status = send_line_message(msg)
            print(f"ステータスコード: {status}")
    else:
        status = send_line_message(text)
        print(f"ステータスコード: {status}")
else:
    text="今回は新着物件がありませんでした。"
    # 追加する文
    intro_text = "🏡新着物件情報のお知らせ🏡\nこんにちは！\n住まいコンシェルジュです✨\n"
    # textの最初に追加
    text = intro_text + text
    last_text="次回の更新もお楽しみに✨"
    text = text + last_text
    # 2. 連続するスペースを1つに統一
    text = re.sub(r'\s+', ' ', text).strip()
    # LINE通知送信
    status = send_line_message(text)
    print(f"ステータスコード: {status}")