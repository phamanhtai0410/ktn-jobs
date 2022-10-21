import traceback
import sentry_sdk
from pydash import get
from pymongo import MongoClient
import json

from enums.event import LeaderBoardEvents
from worker import worker
from config import Config
from lib.utils import dt_utcnow

db = MongoClient(Config.MONGO_URI, connect=False)['katana-dapp']

LeaderBoardModel = db['leader_board']
StakingLogsModel = db['staking_logs']
EventModel = db['events']


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
        try:
            EventModel.find_one_and_update(filter={
                'name': "stake"
            }, update={
                '$set': {
                    'updated_time': dt_utcnow(),
                    'updated_by': 'on_stake'
                },
                "$inc": {
                    'total': 1
                }
            }, upsert=True)
        except:
            sentry_sdk.capture_exception()
            traceback.print_exc()
        # NOTE: create staking leader board
        LeaderBoardModel.find_one_and_update(
            {
                'address': _owner,
                'event': _event_name.lower()
            },
            {
                '$set': {
                    'is_stake': True,
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


@worker.task(name='worker.on_un_stake', rate_limit='1000/s')
def on_un_stake(_event):
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
        try:
            EventModel.find_one_and_update(filter={
                'name': "stake"
            }, update={
                '$set': {
                    'updated_time': dt_utcnow(),
                    'updated_by': 'on_un_stake'
                },
                "$inc": {
                    'total': -1
                }
            }, upsert=True)
        except:
            sentry_sdk.capture_exception()
            traceback.print_exc()

        return f"DONE - insert un stake log: {_event}"
    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_un_stake: {_event}"


@worker.task(name='worker.on_un_stake_all', rate_limit='1000/s')
def on_un_stake_all(_event):
    try:
        event = json.loads(_event)
        _tx_hash = get(event, 'transactionHash').lower()
        _contract = get(event, 'address').lower()
        _owner = get(event, 'args.to').lower()
        _quantity = get(event, 'args.quantity').lower()
        _nft_collection = get(event, 'args.nftCollection').lower()
        _event_name = get(event, 'event')
        _block_number = get(event, 'blockNumber')
        _block_time = get(event, 'block_time')

        _staking_log = StakingLogsModel.find_one({
            'event': _event_name,
            'tx_hash': _tx_hash
        })

        if _staking_log:
            return f'DONE - Stake log existed: {_event}'

        # NOTE: Insert staking log
        StakingLogsModel.insert_one({
            'contract': _contract,
            'address': _owner,
            'token_id': None,
            'nft_collection': _nft_collection,
            'event': _event_name,
            'tx_hash': _tx_hash,
            'block_number': _block_number,
            'block_time': _block_time,
            'created_time': dt_utcnow(),
            'created_by': 'staking_worker'
        })
        try:
            EventModel.find_one_and_update(filter={
                'name': "stake"
            }, update={
                '$set': {
                    'updated_time': dt_utcnow(),
                    'updated_by': 'on_un_stake'
                },
                "$inc": {
                    'total': -int(_quantity)
                }
            }, upsert=True)
        except:
            sentry_sdk.capture_exception()
            traceback.print_exc()

        LeaderBoardModel.find_one_and_update(
            {
                'address': _owner,
                'event': LeaderBoardEvents.STAKE
            },
            {
                '$set': {
                    'is_stake': False,
                    'created_by': 'staking_worker',
                    'created_time': dt_utcnow()
                }
            },
            upsert=True
        )

        return f"DONE - un stake all log: {_event}"
    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_un_stake_all: {_event}"


@worker.task(name='worker.on_update_staking_rank', rate_limit='1000/s')
def on_update_staking_rank():
    try:
        _leader_board_stakings = list(LeaderBoardModel.find(
            filter={
                'event': LeaderBoardEvents.STAKE
            },
            sort={
                'point': 1
            }
        ))

        for index, _item in enumerate(_leader_board_stakings):
            LeaderBoardModel.find_one_and_update(
                {
                    'address': get(_item, 'address'),
                    'event': get(_item, 'event')
                },
                {
                    '$set': {
                        'rank': index + 1,
                        'updated_by': 'staking_worker',
                        'updated_time': dt_utcnow()
                    }
                },
                upsert=False
            )

    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_update_staking_rank"
