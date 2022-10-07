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
    SENTRY_DSN = os.getenv('SENTRY_DSN')
    MONGO_URI = os.getenv('MONGO_URI')
    REDIS_CLUSTER = json.loads(os.getenv("REDIS_CLUSTER", '[]'))
    