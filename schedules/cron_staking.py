import json
import sys
import time
import traceback

import requests
import sentry_sdk
import web3
from pydash import get
from pymongo import MongoClient, ReturnDocument
from web3 import Web3


sys.path.append(".")

from enums.event import LeaderBoardEvents
from lib.logger import debug

from config import Config
from lib import dt_utcnow
from tasks import on_update_staking_rank

SLEEP_TIME = 10  # time get data
POINT_DECIMALS = 10**18

db = MongoClient(Config.MONGO_URI, connect=False)['katana-dapp']

LeaderBoardModel = db['leader_board']
if Config.SENTRY_DSN:
    sentry_sdk.init(Config.SENTRY_DSN)


def add_point(address, amount, ref_id):
    try:
        res = requests.post(f'{Config.IAPI_WALLET}/point', json={
            "amount": amount,
            "ref_id": ref_id,
            "action": LeaderBoardEvents.STAKE,
            "address": address.lower(),
            'event': 'stake'
        }, timeout=10)
        if res.status_code != 200:
            sentry_sdk.capture_message(f"ERROR: send add point {res.text} for user {address} amount {amount}")
    except:
        sentry_sdk.capture_exception()
        traceback.print_exc()


def cron():
    print(f'# start cron price: {dt_utcnow().strftime("%H:%M:%S %d/%m/%Y")}')
    _rpc = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    _contract_address = Config.STAKING_CONTRACT
    _web3 = Web3(Web3.HTTPProvider(_rpc))

    with open('abis/katana_staking.json') as file:
        contract_json = json.load(file)

    if not contract_json:
        raise Exception(f'Not found file abi abis/katana_staking.json')

    _staking_contract = _web3.eth.contract(address=_contract_address, abi=contract_json)

    _staking_boards = LeaderBoardModel.find({
        'event': LeaderBoardEvents.STAKE
    })

    for _staking_board in _staking_boards:
        _user_address = get(_staking_board, 'address')
        _check_sum_user_address = web3.Web3.toChecksumAddress(_user_address)
        _point = _staking_contract.functions.availableRewards(_check_sum_user_address).call()
        if not isinstance(_point, int):
            _point = int(_point)

        _point_formatted = round(_point / POINT_DECIMALS, 2)

        before = LeaderBoardModel.find_one_and_update(
            {
                'address': _user_address,
                'event': LeaderBoardEvents.STAKE
            },
            {
                '$set': {
                    'point': _point_formatted,
                    'updated_by': 'staking_cron',
                    'updated_time': dt_utcnow()
                }
            },
            return_document=ReturnDocument.BEFORE
        )
        _dev_point = _point_formatted - get(before, 'point', 0)
        debug(f"_dev_point of address {_user_address} {_dev_point} {_point_formatted} {get(before, 'point', 0)}")
        if _dev_point > 0:
            add_point(address=_user_address, amount=_dev_point, ref_id=str(get(before, '_id')))

    on_update_staking_rank.delay()
    print(f'# done cron update stake ranking')


while True:
    try:
        print('-' * 10, 'CRON UPDATE STAKE RANKING', '-' * 10)
        cron()
    except:
        sentry_sdk.capture_exception()
        traceback.print_exc()
    time.sleep(SLEEP_TIME)
