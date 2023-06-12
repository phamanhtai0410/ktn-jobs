
import time
import sys

import pydash as py_
import sentry_sdk

sys.path.append(".")
from config import Config

from lib.utils import dt_utcnow
from tasks.price_pairs import on_save_price

from util.request import RequestUtil
if Config.SENTRY_DSN:
    sentry_sdk.init(Config.SENTRY_DSN)


CMC = {
        "name": "Coingecko",
        "url": "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=binancecoin,tether,wbnb"
    }


SLEEP_TIME = 15 # time get data

SYMBOLS = ["usdt", "wbnb", "bnb" ]
PAIRS = ["USDT-USD", "WBNB-USD", "BNB-USD"]

def get_price_data(dex):
    _url = py_.get(dex, 'url')
    _price_response = RequestUtil.get(url_request=_url)

    if not _price_response:
        return None
    print(dex)
    return {
        **dex,
        'price_response': _price_response
    }

def cron():
    print(f'# start cron price: {dt_utcnow().strftime("%H:%M:%S %d/%m/%Y")}')
    print(f'# pairs: {PAIRS}')
    print(f'# dex: {CMC}')
    _prices_data = get_price_data(dex=CMC)
    for _price in _prices_data.get("price_response"):
        _msg = {}
        _msg["name"] = _prices_data["name"]
        _msg["url"] = _prices_data["url"]
        _msg["price_response"] = _price
        on_save_price.delay(price_data=_msg, pairs=PAIRS)
    print(f'# done cron price')

while True:
    print('-'*10, 'CRON PRICE', '-'*10)
    cron()
    time.sleep(SLEEP_TIME)