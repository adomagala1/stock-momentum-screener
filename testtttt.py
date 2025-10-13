from pymongo import MongoClient
uri = "mongodb+srv://haslo:haslo@cluster0.ehoobfy.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)
db = client[""]
print(db.list_collection_names())