import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def list_mongo():
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    
    dbs = await client.list_database_names()
    print(f"Databases: {dbs}")
    
    for db_name in dbs:
        if db_name in ["admin", "local", "config"]:
            continue
        db = client[db_name]
        cols = await db.list_collection_names()
        print(f"Database: {db_name} | Collections: {cols}")
        for col_name in cols:
            count = await db[col_name].count_documents({})
            print(f"  - {col_name}: {count} docs")

if __name__ == "__main__":
    asyncio.run(list_mongo())
