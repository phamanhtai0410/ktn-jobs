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
        'worker.on_stake': {'queue': 'ktn-staking-queue'},
        'worker.on_save_price': {'queue': 'ktn-price-queue'},
        
    }

    REDIS_CLUSTER = json.loads(os.getenv("REDIS_CLUSTER", '[]'))
    REDLOCK_REDIS = json.loads(os.getenv("REDLOCK_REDIS", '[]'))
    
    RPC_URIS = json.loads(os.getenv('RPC_URIS', default='[]'))
    
    KATANA_NFT_CONTRACT = os.getenv('KATANA_NFT_CONTRACT')
    STAKING_CONTRACT = os.getenv('STAKING_CONTRACT')
