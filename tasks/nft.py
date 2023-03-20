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
        _nft_index = py_.get(event, 'args.nftIndex', 0)
        
        _contract = py_.get(event, 'address').lower()
        _event_name = py_.get(event, 'event')
        _block_number = py_.get(event, 'blockNumber')
        _block_time = py_.get(event, 'block_time')
        _extra_data = py_.get(event, 'extra_data', {})
    
        _token_uri = f"{Config.S3_STATIC}/metadata/{_contract}/{_token_id}.json"

        _nft_history = NftsHistoryModel.find_one({
            'token_id': _token_id,
            'event': _event_name,
            'tx_hash': _tx_hash
        })

        if _nft_history:
            return f'DONE - TokenCreated log existed: {_event}'

        """
            NOTE: Add upload the metadata file for each tokenId when it's created
            Updated: Mar 13th, 2023
        """
        # Get the infos stored in DB
        _collection = CollectionModel.find_one(filter={
            "address": _contract
        })
        _types_list = py_.get(_collection, "types_list")
        _chosen_type = _types_list[_nft_index]
        _image = py_.get(_chosen_type, "ImageUrl")
        _animation_url = py_.get(_chosen_type, "AnimationModelUrl")

        # pop the unnecessary infos in `attributes`
        _chosen_type.pop("rate")
        _chosen_type.pop("ImageUrl")
        _chosen_type.pop("AnimationModelUrl")
        _chosen_type.pop("AssetDescription")

        # structure the `metadata` object for message
        _metadata = {
            "name": py_.get(_collection, "name"),
            "description": py_.get(_collection, "description"),
            "image": _image,
            "animation_url": _animation_url,
            "attributes": _chosen_type
        }

        # Full-message to task upload metadata
        _msg_update_meta_data = {
            "contract": _contract,
            "token_id": _token_id,
            "metadata": _metadata
        }

        # Push mess to queue `upload_metadata_nft`
        on_upload_metadata_nft.delay(json.dumps(_msg_update_meta_data)) # upload metadata to s3
        
        # NOTE: statistic data
        _nft_price = NFTPricesModel.find_one({
            "contract": _contract,
            "nft_index": _nft_index
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

@worker.task(bind=True, name='worker.on_mint_from_box', rate_limit='1000/s', max_retries=3)
def on_mint_from_box(self, _event):
    try:
        event = json.loads(_event)
        _contract = py_.get(event, 'contract').lower()
        _tx_hash = py_.get(event, 'transactionHash').lower()
        _event_name = py_.get(event, 'event')
        _block_number = py_.get(event, 'blockNumber')
        _block_time = py_.get(event, 'block_time')
        _extra_data = py_.get(event, 'extra_data', {})

        # Event's data
        _to_public_address = py_.get(event, 'args.to').lower()
        _random_numbers = py_.get(event, 'args.randomNumber', [])
        _token_ids = py_.get(event, 'args.mintedTokenId', [])
        
        for idx, _token_id in enumerate(_token_ids):
            _token_uri = f"{Config.S3_STATIC}/metadata/{_contract}/{_token_id}.json"
            _random = _random_numbers[idx]

            _collection = CollectionModel.find_one(filter={
                "address": _contract
            })
            _types_list = py_.get(_collection, "types_list")
            _rates = [py_.get(_type, "rate") for _type in _types_list]
            
            # Check if event already was saved in to logs
            _nft_history = NftsHistoryModel.find_one({
                'token_id': _token_id,
                'event': _event_name,
                'tx_hash': _tx_hash
            })
            if _nft_history:
                return f'DONE - TokenCreated log existed: {_event}'

            # Metadata for random opening
            _result_idx = check_result_random(_rates, _random)
            _chosen_type = _types_list[_result_idx]

            # get some attributes
            _image = py_.get(_chosen_type, "ImageUrl")
            _animation_url = py_.get(_chosen_type, "AnimationModelUrl")

            # pop the unnecessary infos in `attributes`
            _chosen_type.pop("rate")
            _chosen_type.pop("ImageUrl")
            _chosen_type.pop("AnimationModelUrl")
            _chosen_type.pop("AssetDescription")

            # structure the `metadata` object for message
            _metadata = {
                "name": py_.get(_collection, "name"),
                "description": py_.get(_collection, "description"),
                "image": _image,
                "animation_url": _animation_url,
                "attributes": _chosen_type
            }

            # Full-message to task upload metadata
            _msg_update_meta_data = {
                "contract": _contract,
                "token_id": _token_id,
                "metadata": _metadata
            }
            on_upload_metadata_nft.delay(json.dumps(_msg_update_meta_data)) # upload metadata to s3
            
            # NOTE: statistic data
            _nft_price = NFTPricesModel.find_one({
                "contract": _contract,
                "nft_index": _result_idx
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
            NftsModel.find_one_and_update(
                {
                    'token_id': _token_id,
                    'contract': _contract,
                },
                {
                    '$set': {
                        **_extra_data,
                        'token_id': _token_id,
                        'address': _to_public_address,
                        'contract': _contract,
                        "nft_index": _result_idx,
                        'token_uri': _token_uri,
                        'created_by': 'nft_worker',
                        'created_time': dt_utcnow(),
                    }
                },
                upsert=True
            )

        return f"DONE - Mint NFT From Box Success: {_event}"
    except Exception as exc:
        self.retry(countdown=2, exc=exc)
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_mint_from_box: {_event}"
    
@worker.task(bind=True, name='worker.on_upload_metadata_nft', rate_limit='1000/s', max_retries=3)
def on_upload_metadata_nft(self, _event_infos):
    try:
        event = json.loads(_event_infos)
        _contract_address = py_.get(event, 'contract').lower()
        _token_id = py_.get(event, 'token_id')
        _metadata =  py_.get(event, 'metadata')
        _key = f"metadata/{_contract_address}/{_token_id}.json"
        LoggerTask.debug(f' + path upload metadata NFT: {_key}')

        s3.put_object(
            Bucket=Config.BUCKET_NAME,
            Key=_key,
            Body=json.dumps(_metadata),
            ContentType='application/json'
        )
        return f"DONE - update metadata NFT to S3 with info: {_event_infos}"
    except Exception as exc:
        self.retry(countdown=2, exc=exc)
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_upload_metadata_nft: {_event_infos}"

