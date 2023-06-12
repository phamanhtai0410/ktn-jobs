import random

from celery import Celery
from tasks.nft import on_upload_metadata_nft

app = Celery('add', broker='redis://localhost:6379/0')

@app.task(bind=True)
def add(self, x, y):
	# Get a random number between 1 and 10
	num = random.randint(1, 10)
	print(num) # To help properly understand output
	try:
		# If number is odd, fail the task
		if num % 2:
			raise Exception()
		# If number is even, succeed the task
		else:
			return x + y
	except Exception as e:
		self.retry(countdown=2, exc=e, max_retries=1)
  
if __name__ == "__main__":
    # add.delay(3, 4)
    test = {"contract": "0xbc78541a00f02ab11b0d8a6f038630840a9f80b2",
	"token_id": 3}
    import json
    on_upload_metadata_nft.delay(json.dumps(test))

# _data = {
#             "contract": "0x0adb7475785bdd7535fe7758d3239afb459a2e00",
#             "type": "BOX",
#             "rarity": 0,
#             "is_rarity": False,
#             "price": 1.2
#         }
#         _data1 = {
#             "contract": "0x081e9344a9f130598a97ad65b7bbe857d1b4ebd6",
#             "type": "NFT",
#             "rarity": 1,
#             "is_rarity": True,
#             "price": 1.2
#         }
#         _data2 = {
#             "contract": "0x081e9344a9f130598a97ad65b7bbe857d1b4ebd6",
#             "type": "NFT",
#             "rarity": 2,
#             "is_rarity": True,
#             "price": 1.4
#         }
#         NFTPrices.insert_many([_data, _data1, _data2])