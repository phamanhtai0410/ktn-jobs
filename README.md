Sync cache
===


Run: 
```commandline
        Run script: python3 sync/collection.py db=<db name> col=<collection name> key_sync=<list keys form filter> hset_field=<field_key> tll=-1
        Note:
            - key_sync=user_id - with data-based user id
            - key_sync=on_market#true - with on_market=true is required, it doesn't change
       
        EX:
            Run:  python3 sync/collection.py db=core col=users key_sync=on_market#true type=_id  tll=-1

            Model.find(filter={"on_market": True}, hset_field='_id')
```