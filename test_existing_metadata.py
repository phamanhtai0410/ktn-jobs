import requests
import pydash as py_

_collection = {
    "_id": "644ce498ab468cce8ab00af5",
    "collection_id": 22,
    "name": "Testing Forging - existing metadata files",
    "symbol": "KTN_21",
    "description": "This is the description to test the existing metadata",
    "is_exisiting_metadata": True,
    "display_url": "https://nft.katanainu.com/assets/img/images/38431.gif",
    "image_base_url": "https://teal-keen-gull-392.mypinata.cloud/ipfs/Qmdf2UGgPTzFJS2sgFuojXLpnHMpm5gzGkLtrJDoF5s2Vv",
    "json_base_url": "https://katanainu.com/KatanaInu_Forging_Gen1_Metadata",
    "category": "character",
    "commission": 10,
    "commission_level_2": 10,
    "discount": 4,
    "deployed": False,
    "royalty_rate": 20,
    "total_supply": 10000,
    "created_by": "game_api.exisiting_metadata.22",
    "created_time": "2023-04-29T09:34:16.001Z",
    "updated_time": "2023-04-29T09:34:16.001Z"
}

_token_id = 12
print(f"{py_.get(_collection, 'json_base_url')}/{_token_id}.json")

_headers = {
    'Accept': 'application/json',
    'Access-Control-Allow-Origin': '*'
}

_json = requests.get(
    url=f"{py_.get(_collection, 'json_base_url')}/{_token_id}.json",
    headers=_headers
)
print(_json.__dict__)
print("* JSON = ", _json.json())

_image_url = f"{py_.get(_collection, 'image_base_url')}/{_token_id}.jpg"

_new_json = {
    **_json.json(),
    'image': _image_url
}

print("* NEW JSON : ", _new_json)