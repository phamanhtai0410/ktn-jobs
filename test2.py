from config import Config
import boto3
import json
import pydash as py_
import requests


s3 = boto3.client(
    "s3",
    aws_access_key_id=Config.AWS_KEY,
    aws_secret_access_key=Config.AWS_SECRET,
    endpoint_url=Config.S3_HOST,
    use_ssl=False,
)
def main():
    _json_base = 'https://metadata.katanainu.com/KatanaInu_Forging_Gen1_Metadata'
    _image_base = 'https://teal-keen-gull-392.mypinata.cloud/ipfs/QmUub9waWZJp9J2Nx2h7BL43RShNFsNX56G4xDM6Kc4Ykm'
    for tokenID in range(1, 55):
        
        _headers = {
            'Accept': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
        _json_data = requests.get(
            url=f"{_json_base}/{tokenID}.json",
            headers=_headers
        )
        _image_url = f"{_image_base}/{tokenID}.jpg"
        
        _new_json = {
            **_json_data.json(),
            'image': _image_url
        }
        print(tokenID, _new_json)
        _contract_address = "0x30B42d199AEcEaEfeAE636F44662e1aA6D147F53".lower()
        
        _key = f"metadata/{_contract_address}/{tokenID}.json"
        
        s3.put_object(
            Bucket=Config.BUCKET_NAME,
            Key=_key,
            Body=json.dumps(_new_json),
            ContentType='application/json'
        )

        print(f"DONE - update metadata NFT to S3: {Config.S3_STATIC}/{_key}")

if __name__ == "__main__":
    main()