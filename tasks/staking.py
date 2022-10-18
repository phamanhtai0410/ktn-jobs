import traceback
import sentry_sdk
from pydash import get
from pymongo import MongoClient
import json

from worker import worker
from config import Config
from lib.utils import dt_utcnow

db = MongoClient(Config.MONGO_URI, connect=False)['katana-dapp']

LeaderBoardModel = db['leader_board']
StakingLogsModel = db['staking_logs']


@worker.task(name='worker.on_stake', rate_limit='1000/s')
def on_stake(_event):
    try:
        event = json.loads(_event)
        _tx_hash = get(event, 'transactionHash').lower()
        _token_id = get(event, 'args.tokenId')
        _contract = get(event, 'address').lower()
        _owner = get(event, 'args.to').lower()
        _nft_collection = get(event, 'args.nftCollection').lower()
        _event_name = get(event, 'event')
        _block_number = get(event, 'blockNumber')
        _block_time = get(event, 'block_time')

        _staking_log = StakingLogsModel.find_one({
            'token_id': _token_id,
            'event': _event_name,
            'tx_hash': _tx_hash
        })

        if _staking_log:
            return f'DONE - Stake log existed: {_event}'

        # NOTE: Insert staking log
        StakingLogsModel.insert_one({
            'contract': _contract,
            'address': _owner,
            'token_id': _token_id,
            'nft_collection': _nft_collection,
            'event': _event_name,
            'tx_hash': _tx_hash,
            'block_number': _block_number,
            'block_time': _block_time,
            'created_time': dt_utcnow(),
            'created_by': 'staking_worker'
        })

        # NOTE: create staking leader board
        LeaderBoardModel.find_one_and_update(
            {
                'address': _owner
            },
            {
                '$set': {
                    'event': _event_name.lower(),
                    'point': 0,
                    'rank': 0,
                    'created_by': 'staking_worker',
                    'created_time': dt_utcnow()
                }
            },
            upsert=True
        )

        return f"DONE - insert stake log: {_event}"
    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_stake: {_event}"


@worker.task(name='worker.on_update_staking_rank', rate_limit='1000/s')
def on_update_staking_rank():
    try:
        _leader_board_stakings = list(LeaderBoardModel.find(
            filter={
                'event': 'stake'
            },
            sort={
                'point': 1
            }
        ))
        _max_rank = len(_leader_board_stakings)

        for _item in _leader_board_stakings:
            LeaderBoardModel.find_one_and_update(
                {
                    'address': get(_item, 'address')
                },
                {
                    '$set': {
                        'rank': _max_rank,
                        'updated_by': 'staking_worker',
                        'updated_time': dt_utcnow()
                    }
                },
                upsert=False
            )
            _max_rank = _max_rank - 1

    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_update_staking_rank"
