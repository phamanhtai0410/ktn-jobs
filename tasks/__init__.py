# -*- coding: utf-8 -*-
"""
   Description:
        -
        -
"""
from .nft import on_transfer_nft, on_token_created
from .price_pairs import on_save_price
from .staking import on_stake, on_update_staking_rank
from .referral import send_referral_reward
