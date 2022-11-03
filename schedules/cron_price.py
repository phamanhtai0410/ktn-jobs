
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

DEX_LIST = [
    {
        "name": "Binance",
        "url": "https://www.binance.com/bapi/composite/v1/public/marketing/symbol/list"
    }
]

SLEEP_TIME = 5 # time get data

PAIRS = ["BNBBUSD", "ETHBUSD"]

def get_price_data(dex):
    _url = py_.get(dex, 'url')
    _price_response = RequestUtil.get(url_request=_url)

    if not _price_response:
        return None
    
    return {
        **dex,
        'price_response': _price_response
    }

def cron():
    print(f'# start cron price: {dt_utcnow().strftime("%H:%M:%S %d/%m/%Y")}')
    print(f'# pairs: {PAIRS}')
    print(f'# dex: {DEX_LIST}')
    for dex in DEX_LIST:
        _price_data = get_price_data(dex=dex)
        on_save_price.delay(price_data=_price_data, pairs=PAIRS)
    print(f'# done cron price')

while True:
    print('-'*10, 'CRON PRICE', '-'*10)
    cron()
    time.sleep(SLEEP_TIME)