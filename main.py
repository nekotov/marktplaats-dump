import math
import re

import requests
import json
import sqlite3
import time
from html import escape
cookies = {
    'luckynumber': '815766385',
    'pc': '',
    'MpSession': '000327da-a37d-4b6d-be69-ff7ca58a9ac9',
    'MpHpInitialFeed': '0',
    'rbzid': 'AbIXVgiDz8Pq1u/gloRTgHBZdXLNccSafOqtlp23nfcwV+5+Ncn8cguU8Z7kop1eK4JUS2qZ6197mJOqRoOjw80kjOta0FrD1mKMSzYuPwwTXyC7pA0iYOiNQrPgLvWJ/RPE2stZg/uIEU44MI9rWPRy5qeZv4+ounMYe6kvwgFsFSYlN2u+3qXFJ+x3VSlu2zb7RAlqslz71vxFIJS6eZcevemDRa8kwrThpB8Zfi8=',
    'rbzsessionid': '80f8ab00fd98a649fd2f1482daab2867',
    'G_ENABLED_IDPS': 'google',
}
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    # 'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.marktplaats.nl/l/audio-tv-en-foto/fotocamera-s-digitaal/',
    'DNT': '1',
    'Connection': 'keep-alive',
    # Requests sorts cookies= alphabetically
    # 'Cookie': 'luckynumber=815766385; pc=; MpSession=000327da-a37d-4b6d-be69-ff7ca58a9ac9; MpHpInitialFeed=0; rbzid=AbIXVgiDz8Pq1u/gloRTgHBZdXLNccSafOqtlp23nfcwV+5+Ncn8cguU8Z7kop1eK4JUS2qZ6197mJOqRoOjw80kjOta0FrD1mKMSzYuPwwTXyC7pA0iYOiNQrPgLvWJ/RPE2stZg/uIEU44MI9rWPRy5qeZv4+ounMYe6kvwgFsFSYlN2u+3qXFJ+x3VSlu2zb7RAlqslz71vxFIJS6eZcevemDRa8kwrThpB8Zfi8=; rbzsessionid=80f8ab00fd98a649fd2f1482daab2867',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
}

def progress_bar(current, total, bar_length=20):
    #print(f"PROGRESS BAR {current} {total} <--")
    fraction = current / total

    arrow = int(fraction * bar_length - 1) * '-' + '>'
    padding = int(bar_length - len(arrow)) * ' '

    ending = '\n' if current == total else '\r'

    print(f'Progress: [{arrow}{padding}] {int(fraction*100)}%', end=ending)

url = input("URL: ")
while True:
    req = requests.get(url, headers=headers,cookies=cookies)
    if req.status_code != 200:
        time.sleep(5)
    else:
        break
data_url = req.text
l1CategoryId = re.findall(r"{\"l1CategoryId\":(.*?),", data_url)[0]
l2CategoryId = re.findall(r",\"l2CategoryId\":(.*?),", data_url)
query = ""
done_count = 0
if "#q:" in url:
    query = re.findall(r"/#q:(.*?.*)", url)[0]
    query.replace("+", " ")
total_resp = int(json.loads(requests.get(f"https://www.marktplaats.nl/lrp/api/search?l1CategoryId={l1CategoryId}{'&l2CategoryId='+str(l2CategoryId[0]) if len(l2CategoryId)>0 else ''}&limit=1&offset=0&query={escape(query)}&searchInTitleAndDescription=true&viewOptions=list-view",cookies=cookies,headers=headers).text)["totalResultCount"])

print(f"Total amount of products: {total_resp}")

con = sqlite3.connect(f"{time.time_ns()}.db")
cur = con.cursor()
sq_param = """INSERT INTO {} ("title","price","url") VALUES (?,?,?);"""
table_list = []
sq_db = """CREATE TABLE "{}" (
	"title"	TEXT NOT NULL,
	"price"	REAL NOT NULL,
	"url"	TEXT NOT NULL UNIQUE
);"""




# Auto size. if num<100 -> ret num. if num>100 -> ret 100
auto_size = int(math.ceil(total_resp / 100.0)) * 100 if total_resp>100 else total_resp
sortOrder = ["PRICE", "SORT_INDEX", "OPTIMIZED"]
order = ["INCREASING", "DECREASING"]
auto_order = 0
idl = -1
while idl < auto_size:
    idl+=1
    session = requests.session()


    params = {
        'l1CategoryId': f'{l1CategoryId}',
        'limit': '100',
        'offset': f'{idl*100}',
        'searchInTitleAndDescription': 'true',
        'sortBy': f'{sortOrder[auto_order%3]}',
        'query': f'{query}',
        'sortOrder': order[1 if auto_order>=3 else 0],
        'viewOptions': 'list-view',
    }
    if len(l2CategoryId)>0:
        params['l2CategoryId'] = str(l2CategoryId[0])

    while True:
        response = session.get('https://www.marktplaats.nl/lrp/api/search', params=params, headers=headers, cookies=cookies)
        if response.status_code != 200:
            response = requests.get(response.url, headers=headers, cookies=cookies)
            if response.status_code != 200:
                time.sleep(15)
            else:
                break
        else:
            break
    resp = json.loads(response.text)
    for i in resp["listings"]:
        if json.loads(json.dumps(i))["priceInfo"]["priceType"] not in table_list:
            cur.execute(sq_db.format(json.loads(json.dumps(i))["priceInfo"]["priceType"]))
            con.commit()
            table_list.append(json.loads(json.dumps(i))["priceInfo"]["priceType"])
        if json.loads(json.dumps(i))["sellerInformation"]["showWebsiteUrl"]:
            if "WebSite" not in table_list:
                cur.execute(sq_db.format("WebSite"))
                con.commit()
                table_list.append("WebSite")
            try:
                cur.execute(sq_param.format("WebSite"),
                            [json.loads(json.dumps(i))["title"],
                             int(json.loads(json.dumps(i))["priceInfo"]["priceCents"]) / 100,
                             "https://www.marktplaats.nl" + json.loads(json.dumps(i))["vipUrl"]])
            except:
                continue
            continue
        try:
            cur.execute(sq_param.format(json.loads(json.dumps(i))["priceInfo"]["priceType"]),
                        [json.loads(json.dumps(i))["title"],
                         int(json.loads(json.dumps(i))["priceInfo"]["priceCents"]) / 100,
                         "https://www.marktplaats.nl" + json.loads(json.dumps(i))["vipUrl"]])
        except:
            continue
    con.commit()
    done_count += len(resp["listings"])
    progress_bar(done_count, total_resp)
    if done_count >= total_resp:
        exit(0)
    if len(resp["listings"]) == 0:
        print("Real amount of products:", done_count)
        auto_order+=1
        idl = -1
    if auto_order == 6:
        print("Done")
        exit(0)
    #if len(resp["listings"]) < 100 if total_resp>100 else total_resp:
    #    print(f"Dropped speed to {len(resp['listings'])}/{100 if total_resp>100 else total_resp}")
    #    time.sleep(5)
