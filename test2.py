from config import Config
import boto3
import json
import pydash as py_



s3 = boto3.client(
    "s3",
    aws_access_key_id=Config.AWS_KEY,
    aws_secret_access_key=Config.AWS_SECRET,
    endpoint_url=Config.S3_HOST,
    use_ssl=False,
)
def main():
    _contract_address = "0x75a068654a93c33950ebb13c71041b8ed0422b46".lower()
    _key = f"metadata/{_contract_address}/1004.json"
    with open('test/test.json.gz', 'rb') as f:
        s3.upload_fileobj(
            f,
            Bucket=Config.BUCKET_NAME,
            Key=_key,
            # ContentType='application/json'
        )

    print(f"DONE - update metadata NFT to S3: {Config.S3_STATIC}/{_key}")

if __name__ == "__main__":
    main()