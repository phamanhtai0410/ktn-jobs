# -*- coding: utf-8 -*-
"""
   Description:
        -
        -
"""
from rediscluster import RedisCluster

from config import Config

redis_cluster = RedisCluster(
    startup_nodes=Config.REDIS_CLUSTER,
    decode_responses=True,
    skip_full_coverage_check=True
)
