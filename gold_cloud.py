# -*- coding: utf-8 -*-
"""
7881 平台 · 魔兽世界时光服 · 1区(时光I PvE) · 部落 金币价格云端采集器
GitHub Actions 专用：纯标准库，读写当前目录 gold_price_history.csv，追加一行。
时间统一使用北京时间（UTC+8，固定偏移，不依赖 tzdata）。
"""
import hashlib
import json
import csv
import os
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta

BEIJING = timezone(timedelta(hours=8))
PUB_KEY = "5c2c538a3937c6db2d04bce3d03bbe88bl"[::-1]
API_URL = "https://gw.7881.com/goods-service-api/api/goods/list"
BASE_PARAM = {
    "marketRequestSource": "search",
    "sellerType": "C",
    "gameId": "G6211",           # 魔兽世界时光服
    "gtid": "100001",            # 金币
    "groupId": "G6211P001",      # 时光区
    "serverId": "G6211P001002",  # 时光I(PvE)1区
}
CSV_NAME = "gold_price_history.csv"
FIELDS = ["datetime", "horde_listings", "total_listings", "min_yuan_per_10k",
          "avg_yuan_per_10k", "avg_top10_yuan_per_10k", "median_yuan_per_10k",
          "recycle_max_yuan_per_10k", "recycle_avg3_yuan_per_10k"]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")


def fetch_page(page_num, retries=3):
    for attempt in range(retries):
        ts = int(time.time() * 1000)
        param = dict(BASE_PARAM)
        param["pageNum"] = page_num
        param["pageSize"] = 30
        param["goodsSortType"] = "2"  # 比例最好（单价从低到高）
        body = json.dumps(param, separators=(",", ":"), ensure_ascii=False)
        sign1 = hashlib.md5((PUB_KEY + str(ts)).encode()).hexdigest()
        sign2 = hashlib.md5((sign1 + body).encode()).hexdigest()
        req = urllib.request.Request(API_URL, data=body.encode(), headers={
            "Content-Type": "application/json;charset=UTF-8",
            "lb-timestamp": str(ts),
            "lb-sign": sign2,
            "Origin": "https://search.7881.com",
            "Referer": "https://search.7881.com/G6211-100001-0-0-0.html",
            "User-Agent": UA,
        })
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode("utf-8"))
            if data.get("code") == 0:
                return data["body"]
            print(f"[warn] page {page_num} attempt {attempt+1}: code={data.get('code')} msg={data.get('msg')}")
        except Exception as e:
            print(f"[warn] page {page_num} attempt {attempt+1}: {e}")
        time.sleep(3)
    return None


RECEIPT_URL = ("https://shou.7881.com/ajax/querySearchReceiptGoodsList.htm"
               "?gameId=G6211&goodsType=100001&groupId=G6211P001"
               "&serverId=G6211P001002&campId=bl&t={ts}")


def fetch_recycle(retries=3):
    """回收(收货)频道：币商挂出的收购价，返回元/万金列表（从高到低）。"""
    for attempt in range(retries):
        url = RECEIPT_URL.format(ts=int(time.time() * 1000))
        req = urllib.request.Request(url, headers={
            "Referer": "https://search.7881.com/G6211-100001-0-0-0.html",
            "User-Agent": UA,
        })
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                text = r.read().decode("utf-8", "ignore")
            m = text.find("(")
            data = json.loads(text[m + 1:text.rfind(")")])  # JSONP 去壳
            if data.get("responseCode") == "0000":
                prices = []
                for it in data.get("simpleList") or []:
                    if it.get("campId") == "bl" and it.get("price"):
                        prices.append(float(it["price"]) * 10000)  # 元/万金
                prices.sort(reverse=True)
                return prices
            print(f"[warn] recycle attempt {attempt+1}: {data.get('responseCode')}")
        except Exception as e:
            print(f"[warn] recycle attempt {attempt+1}: {e}")
        time.sleep(3)
    return []


def append_row(row, csv_path):
    new_file = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if new_file:
            w.writeheader()
        w.writerow(row)


def collect():
    body = fetch_page(1)
    if body is None:
        raise RuntimeError("第1页抓取失败")
    total_records = body.get("records", 0)
    items = list(body.get("results") or [])
    body2 = fetch_page(2)
    if body2:
        items.extend(body2.get("results") or [])

    horde = []
    for it in items:
        camp = (it.get("camp") or "").strip()
        title = it.get("title") or ""
        if camp == "部落" or ("【部落】" in title and "【联盟】" not in title):
            pu = it.get("priceOfUnit8") or it.get("priceOfUnit")
            if pu:
                horde.append(float(pu) * 10000)  # 元/万金
    if not horde:
        raise RuntimeError("未筛选到部落商品，7881接口或页面结构可能已变化")

    horde.sort()
    recycle = fetch_recycle()
    now = datetime.now(BEIJING).strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "datetime": now,
        "horde_listings": len(horde),
        "total_listings": total_records,
        "min_yuan_per_10k": round(horde[0], 2),
        "avg_yuan_per_10k": round(statistics.mean(horde), 2),
        "avg_top10_yuan_per_10k": round(statistics.mean(horde[:10]), 2),
        "median_yuan_per_10k": round(statistics.median(horde), 2),
        "recycle_max_yuan_per_10k": round(recycle[0], 2) if recycle else "",
        "recycle_avg3_yuan_per_10k": round(statistics.mean(recycle[:3]), 2) if recycle else "",
    }

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CSV_NAME)
    # 防重：同一分钟内不重复追加（Actions 重试保护）
    if os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        if rows and rows[-1].get("datetime", "")[:16] == now[:16]:
            print(f"[skip] 本分钟已有记录: {now}")
            return rows[-1]
    append_row(row, csv_path)
    print(f"[ok] {now} 售出均价 {row['avg_yuan_per_10k']} / 最低 {row['min_yuan_per_10k']} / 回收最高 {row['recycle_max_yuan_per_10k'] or '-'}")
    return row


if __name__ == "__main__":
    try:
        collect()
    except Exception as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)
