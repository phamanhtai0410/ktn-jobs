from config import Config
import boto3
import json
from pymongo import MongoClient
import pydash as py_
db = MongoClient(Config.MONGO_URI, connect=False)['katana-dapp']



s3 = boto3.client(
    "s3",
    aws_access_key_id=Config.AWS_KEY,
    aws_secret_access_key=Config.AWS_SECRET,
    endpoint_url=Config.S3_HOST,
    use_ssl=False,
)

CollectionModel = db['collection']

def main():
    _contract_address = "0x75a068654a93c33950ebb13c71041b8ed0422b46".lower()
    _collection = CollectionModel.find_one(filter={
        "address": _contract_address
    })
    _nft_index = 0
    _types_list = py_.get(_collection, "types_list")
    _chosen_type = _types_list[_nft_index]
    _image = py_.get(_chosen_type, "ImageUrl")
    _animation_url = py_.get(_chosen_type, "AnimationModelUrl")

    # pop the unnecessary infos in `attributes`
    _chosen_type.pop("rate")
    _chosen_type.pop("ImageUrl")
    _chosen_type.pop("AnimationModelUrl")
    _chosen_type.pop("AssetDescription")
    _metadata = {
            "name": py_.get(_collection, "name"),
            "description": py_.get(_collection, "description"),
            "image": _image,
            "animation_url": _animation_url,
            "attributes": _chosen_type
        }
    print(_metadata)
    _key = f"metadata/{_contract_address}/1001.json"
    s3.put_object(
        Bucket=Config.BUCKET_NAME,
        Key=_key,
        Body=json.dumps(_metadata),
        ContentType='application/json',
        ContentEncoding='gzip'
    )
    print(f"DONE - update metadata NFT to S3: {Config.S3_STATIC}/{_key}")

if __name__ == "__main__":
    main()