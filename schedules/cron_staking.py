import json
import sys
import time

from pydash import get
from pymongo import MongoClient
from web3 import Web3
sys.path.append(".")
from config import Config
from lib import dt_utcnow
from tasks import on_update_staking_rank

SLEEP_TIME = 10  # time get data

db = MongoClient(Config.MONGO_URI, connect=False)['katana-dapp']

LeaderBoardModel = db['leader_board']


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
        'event': 'stake'
    })

    for _staking_board in _staking_boards:
        _user_address = get(_staking_board, 'address')
        _point = _staking_contract.functions.availableRewards(_user_address).call()
        LeaderBoardModel.find_one_and_update(
            {
                'address': _user_address
            },
            {
                '$set': {
                    'point': _point,
                    'updated_by': 'staking_cron',
                    'updated_time': dt_utcnow()
                }
            },
            upsert=False
        )

    on_update_staking_rank.delay()
    print(f'# done cron update stake ranking')


while True:
    print('-' * 10, 'CRON UPDATE STAKE RANKING', '-' * 10)
    cron()
    time.sleep(SLEEP_TIME)
