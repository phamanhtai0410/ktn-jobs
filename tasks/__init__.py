# -*- coding: utf-8 -*-
"""
   Description:
        -
        -
"""
from .nft import on_transfer_nft, on_token_created
from .price_pairs import on_save_price
from .staking import on_stake, on_un_stake, on_un_stake_all, on_update_staking_rank
from .referral import send_referral_reward
from .referral_commission import on_mint_order_from_dev, on_mint_order_from_dapp_creator
from .box import on_created_box, on_open_box, on_transfer_box
from .royalty import on_withdraw_royalty, on_get_info_royalty, on_update_balance_royalty