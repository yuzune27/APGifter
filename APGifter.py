import requests
import time
from datetime import datetime
import settings


class APGifter:
    headers = {
        "appId": "APGifter",
        "appVersion": "1.0.0",
        "Authorization": "Bearer " + settings.access_token,
        "aid": "E1E37924-37F5-48DB-A44B-936964D7169D",
    }


def get_telnum():
    url = "https://api.eonet.jp/mineo/v1/get_telnum_list"

    resp = requests.post(url, headers=APGifter.headers).json()
    return resp["telNumList"]


def get_capacity(cid):
    url = "https://api.eonet.jp/mineo/v1/get_capacity"

    data = {
        "custId": cid,
    }

    resp = requests.post(url, headers=APGifter.headers, data=data).json()
    return resp["packetInfo"]["forwardRemainingCapacity"]


def issue_gift(cid, packet):
    url = "https://api.eonet.jp/mineo/v1/issue_gift"

    data = {
        "custId": cid,
    }

    gcode_list = []
    maxpgift, lastpgift = divmod(packet, 9999)
    for p in range(maxpgift):
        data["giftCapacity"] = 9999
        resp = requests.post(url, headers=APGifter.headers, data=data).json()
        gcode_list.append(resp["giftCode"])
        time.sleep(5)
    data["giftCapacity"] = lastpgift - 10
    resp = requests.post(url, headers=APGifter.headers, data=data).json()
    gcode_list.append(resp["giftCode"])
    return gcode_list


def change_gift(cid, code):  # ギフトコードを受け取る
    url = "https://api.eonet.jp/mineo/v1/change_gift"

    data = {
        "custId": cid,
    }

    for c in code:
        data["giftCode"] = c
        requests.post(url, headers=APGifter.headers, data=data).json()
        time.sleep(5)
    return None


def app_run():
    line_list = []
    cid_list = []

    print("----------------------------------------")
    print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]APGifterを起動しました")
    print("----------------------------------------")
    print("契約回線を取得中……")
    telnum_list = get_telnum()
    print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]契約回線を取得しました。")
    print("----------------------------------------")
    x = 0
    for t in telnum_list:
        print(f"{x}: {t}")
        x += 1
    while True:
        telnum1 = input("1つ目の回線を選択\n-> ")
        try:
            first_linename = telnum_list[int(telnum1)]["lineName"]
            first_cid = telnum_list[int(telnum1)]["custId"]
        except IndexError:
            print("有効な数字を入力してください。")
            continue
        else:
            line_list.append(first_linename)
            cid_list.append(first_cid)  # 一つ目のcid
            print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]1つ目の回線を選択しました。")
            print(f"契約回線：{first_linename}")
            break
    print("--------------------")
    while True:
        telnum2 = input("2つ目の回線を選択\n-> ")
        try:
            second_linename = telnum_list[int(telnum2)]["lineName"]
            second_cid = telnum_list[int(telnum2)]["custId"]  # 二つ目のcid
        except IndexError:
            print("有効な数字を入力してください。")
            continue
        else:
            if second_cid != first_cid:
                line_list.append(second_linename)
                cid_list.append(second_cid)
                print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]2つ目の回線を選択しました。")
                print(f"契約回線：{second_linename}")
                break
            else:
                print("1つ目の回線と違う回線を選択してください。")
    print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]2回線の繰り越し処理を開始します。アプリを終了しないでください。")
    r_count = 1
    for lc in zip(line_list, cid_list):
        print("----------------------------------------")
        linename = lc[0]
        cid = lc[1]
        print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]回線「{linename}」のパケット使用量を取得中……")
        forwardRC = get_capacity(cid)
        print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]取得しました。　残今月末無効パケット: {forwardRC}")
        if forwardRC <= 10:
            print(f"無効パケットが10MB以下のため、ギフトコードを発行する必要はありません。")
            r_count -= 1
            continue
        print("--------------------")

        print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]ギフトコードを発行中……")
        code_list = issue_gift(cid, forwardRC)
        print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]ギフトコードを発行しました。 ギフトコード：{code_list}")
        time.sleep(5)
        print("--------------------")
        print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]回線「{line_list[r_count]}」でパケットギフトを受取中……")
        change_gift(cid_list[r_count], code_list)
        time.sleep(5)
        print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]同量のパケットギフトを返送中……")
        code_list = issue_gift(cid_list[r_count], forwardRC)
        print(
            f"[{datetime.now():%Y/%m/%d %H:%M:%S}]回線「{line_list[r_count]}」でパケットギフトを発行しました。 ギフトコード：{code_list}")
        time.sleep(5)
        print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}回線「{linename}」でパケットギフトを受取中……")
        change_gift(cid, code_list)
        print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]回線「{linename}」の繰り越し処理が完了しました！")
        r_count -= 1

    print("----------------------------------------")
    print(f"[{datetime.now():%Y/%m/%d %H:%M:%S}]全ての処理が完了しました！")
    exit(0)


if __name__ == "__main__":
    app_run()
