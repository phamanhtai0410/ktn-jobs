# -*- coding: utf-8 -*-
"""
   Description:
        -
        -
"""
from datetime import datetime, timezone


def dt_utcnow():
    return datetime.utcnow().replace(tzinfo=timezone.utc)
