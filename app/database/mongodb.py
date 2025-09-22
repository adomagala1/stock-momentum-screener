from pymongo import MongoClient
from app.config import settings

client = MongoClient(settings.mongo_uri)
mongo_db = client[settings.mongo_db]

def get_collection(name: str):
    return mongo_db[name]
