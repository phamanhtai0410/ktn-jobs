# -*- coding: utf-8 -*-
"""
   Description:
        -
        -
"""
import logging
import sys

DEBUG_LEVEL = logging.DEBUG

logger = logging.getLogger('mdb_redis_sync')
logger.setLevel(DEBUG_LEVEL)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(DEBUG_LEVEL)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)