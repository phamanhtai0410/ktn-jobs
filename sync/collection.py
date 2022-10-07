# -*- coding: utf-8 -*-
"""
   Description:
        -
        -
"""
import asyncio
import json
import sys
import traceback

import pymongo
import pydash as py_
from bson import ObjectId, json_util
from pydash import get
import bson.json_util as JsUtil
import sentry_sdk

# Load local package

sys.path.append('.')
from config import Config
from extentions import redis_cluster
from multiprocessing import Pool
from util import logger


def printf(*args):
    logger.debug(f'{args}')


# Default TTL
TTL_KEY = 3 * 86400
printf(f"2. Start watch change in {Config.MONGO_URI}")

# init sentry

sentry_sdk.init(Config.SENTRY_DSN)

ACTION_INSERT = 'insert'
ACTION_UPDATE = 'update'
ACTION_REPLACE = 'replace'
ACTION_DELETE = 'delete'

ACTIONS_WATCH = [
    ACTION_INSERT,
    ACTION_UPDATE,
    ACTION_REPLACE,
    ACTION_DELETE
]


def to_str(x):
    if isinstance(x, ObjectId):
        return str(x)
    if not isinstance(x, str):
        return json_util.dumps(x)
    return x


def get_key_redis(database, collection, obj, fields):
    _filter_keys = []
    _obj = obj.copy()
    for field in fields:
        if "#" not in field:
            _filter_keys.append(field)
        else:
            _key_fields = field.split("#")
            _filter_keys.append(_key_fields[0])
            _obj[_key_fields[0]] = json.loads(_key_fields[1])

    _filter_keys.sort()

    _fields = [f'{x}:{to_str(get(_obj, x, default=""))}' for x in _filter_keys]

    _key = f'{database}.{collection}:{":".join(_fields)}'

    return _key


def func_dumps(obj):
    return JsUtil.dumps(obj)


def func_loads(value):
    return JsUtil.loads(value)


def filter_log(fields, obj):
    _filter_keys = []
    _obj = {}
    for field in fields:
        if "#" in field:
            _key_fields = field.split("#")
            _filter_keys.append(_key_fields[0])
            _obj[_key_fields[0]] = json.loads(_key_fields[1])
    for key, val in _obj.items():
        if obj[key] != val:
            return False
    return True


def handle_log(obj, hset_field, fields, database, collection, ttl=-1, path=None, *args, **kwargs):
    try:
        if not obj:
            return

        key_redis = get_key_redis(database, collection, obj, fields)
        if path:
            value = get(obj, path)
            if not isinstance(value, (str, int, float)):
                value = func_dumps(obj)
        else:
            value = func_dumps(obj)
        if not hset_field:
            _filter = filter_log(obj=obj, fields=fields)
            if not _filter:
                redis_cluster.delete(key_redis)
            else:
                if ttl != -1:
                    redis_cluster.setex(
                        name=key_redis,
                        value=value,
                        time=ttl
                    )
                else:
                    redis_cluster.set(
                        name=key_redis,
                        value=value
                    )
        else:
            _key = get(obj, hset_field)
            if isinstance(_key, ObjectId):
                _key = str(_key)
            _filter = filter_log(obj=obj, fields=fields)

            if _filter:
                printf(f"Add field {_key} with {key_redis}")
                redis_cluster.hset(
                    name=key_redis,
                    key=_key,
                    value=value)
            else:
                printf(f"Remove field {_key} with {key_redis}")

                redis_cluster.hdel(key_redis, _key)
        printf('handle_log', '-' * 5, key_redis)  # for readability only

    except Exception as e:
        sentry_sdk.capture_exception()
        traceback.print_exc()
        printf("Error", str(e))


def loop_task(event):
    _kw = json_util.loads(event)
    handle_log(**_kw)


pool = Pool(50)


def sync_all(database, collection, fields=[], ttl=TTL_KEY, hset_field=None, path=None):
    mdb = pymongo.MongoClient(Config.MONGO_URI)[database]
    # printf("- Start sync all data to redis:",
    #        database, collection, fields, path_sync)
    for obj in mdb[collection].find({}, no_cursor_timeout=True):
        # if not obj['on_market']:
        #     raise Exception
        updated_fields = {}
        if get(obj, 'old_user'):
            updated_fields['old_user'] = get(obj, 'old_user')

        _data = json_util.dumps({
            'obj': obj, 'database': database, 'collection': collection, 'fields': fields,
            'hset_field': hset_field,
            'updated_fields': updated_fields,
            'path': path
        })
        # printf(_data)
        pool.apply_async(loop_task, (_data,))

    printf("- Sync all: SUCCESS")
    printf("-" * 20)


def sync_change(database, collection, fields=[], ttl=TTL_KEY, hset_field=None, path=None):
    printf("- Start monitor & sync change on:", database, collection, fields, ttl)
    mdb = pymongo.MongoClient(Config.MONGO_URI)[database]
    change_stream = mdb[collection].watch([{
        '$match': {
            'operationType': {'$in': ACTIONS_WATCH}
        }
    }], full_document='updateLookup')
    for change in change_stream:
        printf(json_util.dumps(change))
        doc = py_.get(change, 'fullDocument')
        updated_fields = get(change, 'updateDescription.updatedFields') or {}
        _data = json_util.dumps({
            'obj': doc, 'database': database, 'collection': collection, 'fields': fields,
            'hset_field': hset_field,
            'updated_fields': updated_fields,
            'path': path
        })
        pool.apply_async(loop_task, (_data,))


# load options
kw_dict = {}
for arg in sys.argv[1:]:
    if '=' in arg:
        sep = arg.find('=')
        key, value = arg[:sep], arg[sep + 1:]
        kw_dict[key] = value

if __name__ == '__main__':
    _database = get(kw_dict, 'db')
    _collection = get(kw_dict, 'col')
    _key_sync = get(kw_dict, 'key_sync') or []
    if _key_sync and isinstance(_key_sync, str):
        _key_sync = _key_sync.split(',')

    _ttl = int(get(kw_dict, 'ttl', default=f'{TTL_KEY}'))
    key_sync = py_.get(kw_dict, 'key_sync', default='')
    is_sync_all = get(kw_dict, 'is_sync_all', default=True)
    hset_field = get(kw_dict, 'hset_field', default=None)
    path = get(kw_dict, 'path', default=None)

    printf(
        _database, _collection, _key_sync, is_sync_all, hset_field)
    if is_sync_all:
        sync_all(database=_database, collection=_collection, fields=_key_sync, ttl=_ttl,
                 hset_field=hset_field, path=path)
    sync_change(database=_database, collection=_collection, fields=_key_sync, ttl=_ttl,
                hset_field=hset_field, path=path)
