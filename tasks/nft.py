import os
import traceback
import pydash as py_
import sentry_sdk
import json
import web3
import boto3

from constants import Constants
from tasks.referral import send_referral_reward
from pymongo import MongoClient
from worker import worker
from config import Config
from lib.utils import dt_utcnow
from tasks.royalty import on_get_info_royalty
from lib.logger import LoggerTask


db = MongoClient(Config.MONGO_URI, connect=False)['katana-dapp']

NftsModel = db['nfts']
NftsHistoryModel = db['nfts_history']
NftsStatisticsModel = db['nfts_statistics']
MeshModel = db['meshes']
NFTPricesModel = db['nft_prices']
CollectionModel = db['collection']

s3 = boto3.client(
    "s3",
    aws_access_key_id=Config.AWS_KEY,
    aws_secret_access_key=Config.AWS_SECRET,
    endpoint_url=Config.S3_HOST,
    use_ssl=False,
)

def check_result_random(_rates, _random):
    _sum = 0
    for _r in range(len(_rates)):
        if _random > _sum and _random < _sum + _rates[_r]:
            _index = _r
            break
        _sum += _rates[_r]

    return _index
    
@worker.task(name='worker.on_token_created', rate_limit='1000/s')
def on_token_created(_event):
    try:
        event = json.loads(_event)
        _to_public_address = py_.get(event, 'args.to', '').lower()
        _tx_hash = py_.get(event, 'transactionHash').lower()
        _token_id = py_.get(event, 'args.tokenId')
        _contract = py_.get(event, 'address').lower()
        _event_name = py_.get(event, 'event')
        _block_number = py_.get(event, 'blockNumber')
        _block_time = py_.get(event, 'block_time')
        # _token_detail = py_.get(event, 'args.details')
        # _rarity = py_.to_integer(_token_detail[0][0])
        # _mesh_index = py_.to_integer(_token_detail[0][1])
        # _mesh_material = py_.to_integer(_token_detail[0][2])
        # _token_uri = _token_detail[1]
        _extra_data = py_.get(event, 'extra_data', {})
        _token_uri = f"{Config.S3_STATIC}/metadata/{_contract}/{_token_id}.json"
        _nft_index = py_.get(event, 'nftIndex', 0)
        _nft_history = NftsHistoryModel.find_one({
            'token_id': _token_id,
            'event': _event_name,
            'tx_hash': _tx_hash
        })

        if _nft_history:
            return f'DONE - TokenCreated log existed: {_event}'

        # _msg_update_meta_data = {
        #     "contract": _contract,
        #     "token_id": _token_id,
        #     "metadata": {} #[TODO]
        # }
        # on_upload_metadata_nft.delay(json.dumps(_msg_update_meta_data)) # upload metadata to s3
        
        # NOTE: statistic data
        _nft_price = NFTPricesModel.find_one({
            "contract": _contract,
            "rarity": 0 #[TODO]
        })
        _price = py_.get(_nft_price, 'price', 0)
        # Check price NFT && Update NFT [TODO]
        if not _price:
            print(f'`missing` price for contract: {_contract}')
            sentry_sdk.capture_message(f'missing price for contract: {_contract}')
        else:
            NftsStatisticsModel.find_one_and_update({
                'address': _contract
            }, {
                '$inc': {
                    'total': _price
                },
                '$set': {
                    'contract': _contract,
                    'updated_time': dt_utcnow(),
                    'updated_by': 'nft_worker'
                }
            }, upsert=True)

        _insert_result = NftsHistoryModel.insert_one({
            **_extra_data,
            'contract': _contract,
            'from_address': str(web3.constants.ADDRESS_ZERO),
            'to_address': _to_public_address,
            'token_id': _token_id,
            'event': _event_name,
            'tx_hash': _tx_hash,
            'block_number': _block_number,
            'block_time': _block_time,
            'created_time': dt_utcnow(),
            'created_by': 'nft_worker'
        })
        # NOTE: will insert metadata of nft with mint event
        NftsModel.find_one_and_update({
            'token_id': _token_id,
            'contract': _contract,
        },
            {
                '$set': {
                    **_extra_data,
                    'token_id': _token_id,
                    'address': _to_public_address,
                    'contract': _contract,
                    # 'rarity': _rarity,
                    # 'mesh_index': _mesh_index,
                    # 'mesh_material': _mesh_material,
                    "nft_index": _nft_index,
                    'token_uri': _token_uri,
                    'created_by': 'nft_worker',
                    'created_time': dt_utcnow(),
                }}, upsert=True)

        # send_referral_reward.delay(
        #     origin_id=str(py_.get(_insert_result, 'inserted_id')),
        #     address=_to_public_address,
        #     nft_data={
        #         'tx_hash': _tx_hash,
        #         'token_id': _token_id,
        #         'nft_type': _nft_type,
        #         'rarity': _rarity
        #     },
        #     reward_type='TokenCreated')

        return f"DONE - insert nft info: {_event}"
    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_token_created: {_event}"


@worker.task(name='worker.on_transfer_nft', rate_limit='1000/s')
def on_transfer_nft(_event):
    try:
        event = json.loads(_event)
        _from_public_address = py_.get(event, 'args.from', '').lower()
        _to_public_address = py_.get(event, 'args.to', '').lower()
        _token_id = py_.get(event, 'args.tokenId')
        _event_name = py_.get(event, 'event')
        _tx_hash = py_.get(event, 'transactionHash').lower()
        _block_number = py_.get(event, 'blockNumber')
        _block_time = py_.get(event, 'block_time')
        _contract = py_.get(event, 'address').lower()
        _extra_data = py_.get(event, 'extra_data', {})
        
        # add task check balance royalty
        _msg_balance_royalty = {"collection_address": _contract, "tx_hash": _tx_hash}
        on_get_info_royalty.delay(json.dumps(_msg_balance_royalty))
        
        # NOTE: if not mint event will not execute anything
        if _from_public_address == web3.constants.ADDRESS_ZERO:
            return 'DONE - not execute logic with mint action'

        if _to_public_address == Config.STAKING_CONTRACT.lower():
            _event_name = Constants.EVENT_NAME_STAKE

        if _from_public_address == Config.STAKING_CONTRACT.lower():
            _event_name = Constants.EVENT_NAME_UN_STAKE

        nft_history = NftsHistoryModel.find_one({
            'tx_hash': _tx_hash,
            'token_id': _token_id,
            'event': _event_name
        })

        if nft_history:
            return f'DONE - {_event_name} existed: {_event}'

        NftsHistoryModel.insert_one({
            **_extra_data,
            'contract': _contract,
            'from_address': _from_public_address,
            'to_address': _to_public_address,
            'token_id': _token_id,
            'event': _event_name,
            'tx_hash': _tx_hash,
            'block_number': _block_number,
            'block_time': _block_time,
            'created_time': dt_utcnow(),
            'created_by': 'nft_worker'
        })

        if _event_name == Constants.EVENT_NAME_STAKE:
            NftsModel.find_one_and_update({
                'token_id': _token_id,
                'contract': _contract,
            }, {
                '$set': {
                    'is_staking': True,
                    'updated_by': 'nft_worker',
                    'updated_time': dt_utcnow()
                }
            }, upsert=True)
        elif _event_name == Constants.EVENT_NAME_UN_STAKE:
            NftsModel.find_one_and_update({
                'token_id': _token_id,
                'contract': _contract,
            }, {
                '$set': {
                    'is_staking': False,
                    'updated_by': 'nft_worker',
                    'updated_time': dt_utcnow()
                }
            }, upsert=True)
        elif _event_name == Constants.EVENT_NAME_TRANSFER:
            NftsModel.find_one_and_update({
                'token_id': _token_id,
                'contract': _contract,
            }, {
                '$set': {
                    'old_address': _from_public_address,
                    'address': _to_public_address,
                    'updated_by': 'nft_worker',
                    'updated_time': dt_utcnow()
                }}, upsert=True)

        return f"DONE - update owner nft info: {_event}"
    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_transfer_nft: {_event}"


@worker.task(bind=True, name='worker.on_upload_metadata_nft', rate_limit='1000/s', max_retries=3)
def on_upload_metadata_nft(self, _event):
    try:
        event = json.loads(_event)
        _contract_address = py_.get(event, 'contract').lower()
        _token_id = py_.get(event, 'token_id')
        _metadata =  py_.get(event, 'metadata')
        _key = f"metadata/{_contract_address}/{_token_id}.json"
        LoggerTask.debug(f'path upload metadata NFT: {_key}')

        _rate_random = CollectionModel.find_one({
            "address":  "0x081e9344a9f130598a97ad65b7bbe857d1b4ebd6"
        })
        print("test ", _rate_random)
        _rates = py_.get(_rate_random, 'type_list', [])
        if len(_rate_random) > 0:
            # _rates = [i[""] for i in rate]
            # check_result_random()
            _random_nft = 1
            # s3.put_object(
            #     Bucket=Config.BUCKET_NAME,
            #     Key=_key,
            #     Body=json.dumps(_metadata),
            #     ContentType='text/html'
            # )
        return f"DONE - update metadata NFT to S3 with info: {_event}"
    except Exception as exc:
        self.retry(countdown=2, exc=exc)
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_upload_metadata_nft: {_event}"


@worker.task(bind=True, name='worker.on_mint_from_box', rate_limit='1000/s', max_retries=3)
def on_mint_from_box(self, _event):
    try:
        event = json.loads(_event)
        _contract = py_.get(event, 'contract').lower()
        _to_public_address = py_.get(event, 'args.to').lower()
        _random_numbers = py_.get(event, 'args.randomNumber', [])
        _token_ids = py_.get(event, 'args.mintedTokenId', [])
        _tx_hash = py_.get(event, 'transactionHash').lower()
        _event_name = py_.get(event, 'event')
        _block_number = py_.get(event, 'blockNumber')
        _block_time = py_.get(event, 'block_time')
        _extra_data = py_.get(event, 'extra_data', {})
        
        for idx, _token_id in enumerate(_token_ids):
            _token_uri = f"{Config.S3_STATIC}/metadata/{_contract}/{_token_id}.json"
            _nft_index = py_.get(event, 'nftIndex', 0)
            _nft_history = NftsHistoryModel.find_one({
                'token_id': _token_id,
                'event': _event_name,
                'tx_hash': _tx_hash
            })

            if _nft_history:
                return f'DONE - TokenCreated log existed: {_event}'

            # _msg_update_meta_data = {
            #     "contract": _contract,
            #     "token_id": _token_id,
            #     "metadata": {} #[TODO]
            # }
            # on_upload_metadata_nft.delay(json.dumps(_msg_update_meta_data)) # upload metadata to s3
            
            # NOTE: statistic data
            
            _nft_price = NFTPricesModel.find_one({
                "contract": _contract,
                "rarity": 0 #[TODO]
            })
            _price = py_.get(_nft_price, 'price', 0)
            # Check price NFT && Update NFT [TODO]
            if not _price:
                print(f'`missing` price for contract: {_contract}')
                sentry_sdk.capture_message(f'missing price for contract: {_contract}')
            else:
                NftsStatisticsModel.find_one_and_update({
                    'address': _contract
                }, {
                    '$inc': {
                        'total': _price
                    },
                    '$set': {
                        'contract': _contract,
                        'updated_time': dt_utcnow(),
                        'updated_by': 'nft_worker'
                    }
                }, upsert=True)

            _insert_result = NftsHistoryModel.insert_one({
                **_extra_data,
                'contract': _contract,
                'from_address': str(web3.constants.ADDRESS_ZERO),
                'to_address': _to_public_address,
                'token_id': _token_id,
                'event': _event_name,
                'tx_hash': _tx_hash,
                'block_number': _block_number,
                'block_time': _block_time,
                'created_time': dt_utcnow(),
                'created_by': 'nft_worker'
            })
            # NOTE: will insert metadata of nft with mint event
            NftsModel.find_one_and_update({
                'token_id': _token_id,
                'contract': _contract,
            },
                {
                    '$set': {
                        **_extra_data,
                        'token_id': _token_id,
                        'address': _to_public_address,
                        'contract': _contract,
                        "nft_index": _nft_index,
                        'token_uri': _token_uri,
                        'created_by': 'nft_worker',
                        'created_time': dt_utcnow(),
                    }}, upsert=True)


        return f"DONE - Mint NFT From Box Success: {_event}"
    except Exception as exc:
        self.retry(countdown=2, exc=exc)
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_mint_from_box: {_event}"
