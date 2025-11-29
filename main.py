import time
from datetime import datetime
import urllib3
import requests

import settings


class APGifter:
    headers = {
        "appId": "APGifter",
        "appVersion": "1.0.0",
        "Authorization": "Bearer " + settings.access_token,
        "aid": "E1E37924-37F5-48DB-A44B-936964D7169D",
    }


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# SSL証明書検証の問題を解決するためのセッション設定
def create_session():
    session = requests.Session()
    # 通信確認用
    # session.verify = False
    return session


def get_telnum():
    url = "https://api.eonet.jp/mineo/v1/get_telnum_list"

    session = create_session()
    resp = session.post(url, headers=APGifter.headers).json()
    return resp["telNumList"]


def get_capacity(cid):
    url = "https://api.eonet.jp/mineo/v1/get_capacity"

    data = {
        "custId": cid,
    }

    session = create_session()
    resp = session.post(url, headers=APGifter.headers, data=data).json()
    return resp["packetInfo"]["forwardRemainingCapacity"]


def issue_gift(cid, packet):
    url = "https://api.eonet.jp/mineo/v1/issue_gift"

    data = {
        "custId": cid,
    }

    session = create_session()
    gcode_list = []
    maxpgift, lastpgift = divmod(packet, 9999)
    for p in range(maxpgift):
        data["giftCapacity"] = 9999
        resp = session.post(url, headers=APGifter.headers, data=data).json()
        gcode_list.append(resp["giftCode"])
        time.sleep(5)
    data["giftCapacity"] = lastpgift - 10
    resp = session.post(url, headers=APGifter.headers, data=data).json()
    gcode_list.append(resp["giftCode"])
    return gcode_list


def change_gift(cid, code):  # ギフトコードを受け取る
    url = "https://api.eonet.jp/mineo/v1/change_gift"

    data = {
        "custId": cid,
    }

    session = create_session()
    for c in code:
        data["giftCode"] = c
        session.post(url, headers=APGifter.headers, data=data).json()
        time.sleep(5)
    return None


def ref_token():
    url = "https://login.eonet.jp/oidc/v1/token"

    data = {
        "grant_type": "refresh_token",
        "refresh_token": settings.refresh_token,
        "client_id": 100064798
    }

    session = create_session()
    resp = session.post(url, data=data).json()

    settings.os.environ["ACCESS_TOKEN"] = resp["id_token"]
    settings.os.environ["REFRESH_TOKEN"] = resp["refresh_token"]

MIN_PACKET_THRESHOLD = 10
DELAY_SECONDS = 5


def print_log(message, include_timestamp=True):
    """ログメッセージを統一フォーマットで出力"""
    if include_timestamp:
        print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]{message}")
    else:
        print(message)


def display_available_lines(telnum_list):
    """利用可能な回線一覧を表示"""
    for index, line_info in enumerate(telnum_list):
        print(f"{index}: {line_info}")


def select_line(telnum_list, line_number, exclude_cid=None):
    """回線を選択し、回線名とカスタマーIDを返す"""
    while True:
        selection = input(f"{line_number}つ目の回線を選択\n-> ")
        try:
            selected_index = int(selection)
            line_name = telnum_list[selected_index]["lineName"]
            customer_id = telnum_list[selected_index]["custId"]

            if exclude_cid and customer_id == exclude_cid:
                print("1つ目の回線と違う回線を選択してください。")
                continue

            print_log(f"{line_number}つ目の回線を選択しました。")
            print(f"契約回線：{line_name}")
            return line_name, customer_id

        except (IndexError, ValueError):
            print("有効な数字を入力してください。")


def select_lines(telnum_list):
    """2つの回線を選択し、回線情報のリストを返す"""
    display_available_lines(telnum_list)

    # 1つ目の回線選択
    first_line_name, first_cid = select_line(telnum_list, 1)
    print("--------------------")

    # 2つ目の回線選択
    second_line_name, second_cid = select_line(telnum_list, 2, exclude_cid=first_cid)

    return [first_line_name, second_line_name], [first_cid, second_cid]


def process_packet_transfer(line_name, customer_id, target_line_name, target_cid):
    """指定した回線間でパケット転送処理を実行"""
    print("----------------------------------------")
    print_log(f"回線「{line_name}」のパケット使用量を取得中……")

    forward_remaining_capacity = get_capacity(customer_id)
    print_log(f"取得しました。　残今月末無効パケット: {forward_remaining_capacity}")

    if forward_remaining_capacity <= MIN_PACKET_THRESHOLD:
        print(f"無効パケットが{MIN_PACKET_THRESHOLD}MB以下のため、ギフトコードを発行する必要はありません。")
        return False

    print("--------------------")

    # ギフトコード発行
    print_log("ギフトコードを発行中……")
    gift_codes = issue_gift(customer_id, forward_remaining_capacity)
    print_log(f"ギフトコードを発行しました。 ギフトコード：{gift_codes}")
    time.sleep(DELAY_SECONDS)

    print("--------------------")

    # ターゲット回線でギフト受取
    print_log(f"回線「{target_line_name}」でパケットギフトを受取中……")
    change_gift(target_cid, gift_codes)
    time.sleep(DELAY_SECONDS)

    # 返送用ギフトコード発行
    print_log("同量のパケットギフトを返送中……")
    return_gift_codes = issue_gift(target_cid, forward_remaining_capacity)
    print_log(f"回線「{target_line_name}」でパケットギフトを発行しました。 ギフトコード：{return_gift_codes}")
    time.sleep(DELAY_SECONDS)

    # 元の回線でギフト受取
    print_log(f"回線「{line_name}」でパケットギフトを受取中……")
    change_gift(customer_id, return_gift_codes)
    print_log(f"回線「{line_name}」の繰り越し処理が完了しました！")

    return True


def app_run():
    """APGifterのメイン実行関数"""
    print("----------------------------------------")
    print_log("APGifterを起動しました。")
    print("----------------------------------------")

    # 契約回線取得
    print("契約回線を取得中……")
    telnum_list = get_telnum()
    print_log("契約回線を取得しました。")
    print("----------------------------------------")

    # 回線選択
    line_names, customer_ids = select_lines(telnum_list)

    # パケット転送処理開始
    print_log("2回線の繰り越し処理を開始します。アプリを終了しないでください。")

    # 各回線に対してパケット転送処理を実行
    for i in range(len(line_names)):
        target_index = 1 - i  # 0→1, 1→0
        process_packet_transfer(
            line_names[i],
            customer_ids[i],
            line_names[target_index],
            customer_ids[target_index]
        )

    print("----------------------------------------")
    print_log("全ての処理が完了しました！")
    exit(0)

if __name__ == "__main__":
    app_run()