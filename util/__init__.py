# -*- coding: utf-8 -*-
"""
   Description:
        -
        -
"""
from .logger import logger

def make_red_key(tx_hash, contract):
    return f'smc_ktn_log:redlock\{contract}:{tx_hash}'