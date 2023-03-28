from config import Config
# import boto3
import json
from pymongo import MongoClient
import pydash as py_
import random

db = MongoClient(Config.MONGO_URI, connect=False)['katana-dapp']



CollectionModel = db['collection']

def main():
    _total_supply = 110
    rounding_per = int(_total_supply * 0.39) + int(_total_supply * 0.40) + int(_total_supply * 0.21)
    
    # print(_total_supply * 0.39)
    UNCOMMON = ["UNCOMMON" for i in range(int(_total_supply * 0.4))] # 40 %
    RARE = ["RARE" for i in range(int(_total_supply * 0.3))] # 30 %
    MYSTICAL = ["MYSTICAL" for i in range(int(_total_supply * 0.15))]  # 15 %
    LEGENDARY = ["LEGENDARY" for i in range(int(_total_supply * 0.1))] # 10 %
    IMMORTAL = ["IMMORTAL" for i in range(int(_total_supply * 0.05))] # 5 %
    
    _array = UNCOMMON + RARE + MYSTICAL + LEGENDARY + IMMORTAL
    random.shuffle(_array)
    random.shuffle(_array)
    # random.shuffle(_array)
    
    # print("shuffle_array ", _array)
    idx_bc = 13
    _res = _array[idx_bc]
    
    _contract = "0x5D12fFaF4aB3D70B5c3941dd6a29fc6FC4415Eb4"
    _token_id = 1234
    _collection = CollectionModel.find_one(filter={
        "collection_id": 16
    })
    _total_supply = py_.get(_collection, "total_supply")
    _types_list = py_.get(_collection, "types_list")
    _total_supply = 100000
    
    _arr_shuffle = []
    _choose_idxs = [py_.get(_type, "AssetRarity") for _type in  _types_list]
    for _type in _types_list:
        _amount_item = int(_total_supply * (py_.get(_type, "rate") / 100.0))
        _arr_shuffle += [py_.get(_type, "AssetRarity") for i in range(_amount_item)]
    if len(_arr_shuffle) < _total_supply:
        _lost = _total_supply - len(_arr_shuffle)
        _arr_shuffle += [_arr_shuffle[0] for i in range(_lost)]
    # shuffle array
    random.shuffle(_arr_shuffle)
    random.shuffle(_arr_shuffle)
    _choose_rarity = _arr_shuffle[_token_id]
    print("_choose_rarity ", _choose_rarity)
    _choose_idx_type = _choose_idxs.index(_choose_rarity)
    _chosen_type = _types_list[_choose_idx_type]
    print("_chosen_type ", _chosen_type)
    # Metadata for random opening
  
    
    print()
    # get some attributes
    _image = py_.get(_chosen_type, "ImageUrl", "https://ipfs.moralis.io:2053/ipfs/QmXqxN16GhrVtYsMUBH5zVmTdnffQf35dv6v4YKXnZoYG7/event.png")
    _animation_url = py_.get(_chosen_type, "AnimationModelUrl", "https://bafybeidflvqfxkw4zbcnlcxu6mnkbhjxfdecv3ggkj3fgb5bm5nmbhznqu.ipfs.dweb.link/boots.glb")
    _description = py_.get(_collection, "description")
    _price = py_.get(_chosen_type, 'price', 0)

    # pop the unnecessary infos in `attributes`
    _chosen_type.pop("rate")
    _chosen_type.pop("price")
    if py_.get(_chosen_type, "ImageUrl"):
        _chosen_type.pop("ImageUrl")
    if py_.get(_chosen_type, "AnimationModelUrl"):
        _chosen_type.pop("AnimationModelUrl")
    _chosen_type.pop("AssetDescription")

    # structure the `metadata` object for message
    _metadata = {
        "name": py_.get(_collection, "name"),
        "description": _description,
        "image": _image,
        "animation_url": _animation_url,
        "attributes": _chosen_type
    }
        
    # for i in range(5):
        
    # _contract_address = "0x75a068654a93c33950ebb13c71041b8ed0422b46".lower()
    # _collection = CollectionModel.find_one(filter={
    #     "address": _contract_address
    # })
    # _nft_index = 0
    # _types_list = py_.get(_collection, "types_list")
    # _chosen_type = _types_list[_nft_index]
    # _image = py_.get(_chosen_type, "ImageUrl")
    # _animation_url = py_.get(_chosen_type, "AnimationModelUrl")

    # # pop the unnecessary infos in `attributes`
    # _chosen_type.pop("rate")
    # _chosen_type.pop("ImageUrl")
    # _chosen_type.pop("AnimationModelUrl")
    # _chosen_type.pop("AssetDescription")

    # _metadata = {
    #         "name": py_.get(_collection, "name"),
    #         "description": py_.get(_collection, "description"),
    #         "image": _image,
    #         "animation_url": _animation_url,
    #         "attributes": [
    #             {
    #                 "trait_type": _k,
    #                 "value": _v
    #             }
    #             for _k, _v in _chosen_type.items()
    #         ]
    #     }
    # print(

if __name__ == "__main__":
    

    # s=list(range(50))
    # random.shuffle(s) # 1
    # print("shuffle 1 ", s)
    # random.shuffle(s) # 2
    # print("shuffle 2 ", s)
    # random.shuffle(s) # 3
    # print("shuffle 3 ", s)
    # print(s)

    # print: [2, 4, 1, 3, 0]
    main()
    

# db.collection.find({"collection_id": 7})
#    .projection({})
#    .sort({_id:-1})
#    .limit(100)

# db.collection.insert({
# 	"collection_id" : 20,
# 	"name" : "Balance",
# 	"symbol" : "KTN_202",
# 	"description" : "The head",
# 	"types_list":[
	{
		"AssetUniqueIndex" : "",
            "EventDataTableID" : "",
            "AssetDescription" : "The head of a mythical beast sits atop of this mighty axe.",
            "AssetRarity" : "UNCOMMON",
            "AssetID" : "KatanaInuBlueZillaAxes_1",
            "ImageUrl" : "test",
            "DataTableID" : "208",
            "AnimationModelUrl" : "test1",
            "rate" : Double("20"),
            "price" : "10"
        },
        {
            "AssetUniqueIndex" : "",
            "EventDataTableID" : "",
            "AssetDescription" : "The head of a mythical beast sits atop of this mighty axe.",
            "AssetRarity" : "RARE",
            "AssetID" : "KatanaInuBlueZillaAxes_2",
            "ImageUrl" : "test",
            "DataTableID" : "208",
            "AnimationModelUrl" : "test1",
            "rate" : Double("20"),
            "price" : "10"
        },
        {
            "AssetUniqueIndex" : "",
            "EventDataTableID" : "",
            "AssetDescription" : "The head of a mythical beast sits atop of this mighty axe.",
            "AssetRarity" : "MYSTICAL",
            "AssetID" : "KatanaInuBlueZillaAxes_3",
            "ImageUrl" : "test",
            "DataTableID" : "208",
            "AnimationModelUrl" : "test1",
            "rate" : Double("20"),
            "price" : "10"
        },
        {
            "AssetUniqueIndex" : "",
            "EventDataTableID" : "",
            "AssetDescription" : "The head of a mythical beast sits atop of this mighty axe.",
            "AssetRarity" : "LEGENDARY",
            "AssetID" : "KatanaInuBlueZillaAxes_4",
            "ImageUrl" : "test",
            "DataTableID" : "208",
            "AnimationModelUrl" : "test1",
            "rate" : Double("20"),
            "price" : "10"
        },
        {
            "AssetUniqueIndex" : "",
            "EventDataTableID" : "",
            "AssetDescription" : "The head of a mythical beast sits atop of this mighty axe.",
            "AssetRarity" : "IMMORTAL",
            "AssetID" : "KatanaInuBlueZillaAxes_5",
            "ImageUrl" : "test",
            "DataTableID" : "208",
            "AnimationModelUrl" : "test1",
            "rate" : Double("20"),
            "price" : "10"
        }
    ],
	"deployed" : false,
	"royalty_rate" : 2000,
	"total_supply" : 10000,
	"created_by" : "game@launcher",
	"created_time" : ISODate("2023-03-20T10:12:53.762+07:00"),
	"updated_time" : ISODate("2023-03-20T10:12:53.762+07:00"),
	"category" : "Character",
	"chain" : "BSC"
}
)



