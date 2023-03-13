# -*- coding: utf-8 -*-
"""
   Description:
        -
        -
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()


class Config():
    PROJECT = 'ktn-jobs'

    SENTRY_DSN = os.getenv('SENTRY_DSN')
    MONGO_URI = os.getenv('MONGO_URI')
    BROKER_URL = os.getenv('BROKER_URL')

    CELERY_IMPORTS = ['tasks']
    CELERY_QUEUES = os.getenv('CELERY_QUEUES')

    CELERY_ROUTES = {
        'worker.on_transfer_nft': {'queue': 'ktn-nft-queue'},
        'worker.on_token_created': {'queue': 'ktn-nft-queue'},
        'worker.on_upload_metadata_nft': {'queue': 'ktn-nft-queue'},
        'worker.on_mint_from_box': {'queue': 'ktn-nft-queue'},
        'worker.on_stake': {'queue': 'ktn-staking-queue'},
        'worker.on_un_stake': {'queue': 'ktn-staking-queue'},
        'worker.on_un_stake_all': {'queue': 'ktn-staking-queue'},
        'worker.on_update_staking_rank': {'queue': 'ktn-staking-queue'},
        'worker.on_save_price': {'queue': 'ktn-price-queue'},
        'worker.send_referral_reward': {'queue': 'ktn-jobs-queue'},
        'worker.on_mint_order_from_dev': {'queue': 'ktn-referral-commission-queue'},
        'worker.on_mint_order_from_dapp_creator': {'queue': 'ktn-referral-commission-queue'},
        'worker.on_created_box': {'queue': 'ktn-nft-queue'},
        'worker.on_transfer_box': {'queue': 'ktn-nft-queue'},
        'worker.on_open_box': {'queue': 'ktn-nft-queue'},
        
        'worker.on_withdraw_royalty': {'queue': 'ktn-withdraw-royalty'},
        'worker.on_get_info_royalty': {'queue': 'ktn-get-info-royalty'},
        'worker.on_update_balance_royalty': {'queue': 'ktn-update-balance-royalty'},
    }

    REDIS_CLUSTER = json.loads(os.getenv("REDIS_CLUSTER", '[]'))
    REDLOCK_REDIS = json.loads(os.getenv("REDLOCK_REDIS", '[]'))
    
    RPC_URIS = json.loads(os.getenv('RPC_URIS', default='[]'))
    
    KATANA_NFT_CONTRACT = os.getenv('KATANA_NFT_CONTRACT')
    STAKING_CONTRACT = os.getenv('STAKING_CONTRACT')
    TREASURY_ROYALTY_CONTRACT = os.getenv('TREASURY_ROYALTY_CONTRACT')
    TOKEN_USDT = os.getenv('TOKEN_USDT')
    TOKEN_WBNB = os.getenv('TOKEN_WBNB')
    IAPI_WALLET = os.getenv('IAPI_WALLET')
    
    # S3
    AWS_KEY = os.getenv('AWS_KEY')
    AWS_SECRET = os.getenv('AWS_SECRET')
    BUCKET_NAME = os.getenv('BUCKET_NAME')
    S3_HOST = os.getenv('S3_HOST')
    S3_STATIC = os.getenv('S3_STATIC')