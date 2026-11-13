from pymongo import AsyncMongoClient
from app.core.config import settings

client = None
database = None

async def connect_to_mongo():
    global client, database
    client = AsyncMongoClient(settings.mongodb_uri)
    database = client[settings.mongodb_database]
    try:
        await client.admin.command("ping")
        await database.users.create_index("email", unique=True)
        await database.resumes.create_index([("user_id", 1), ("created_at", -1)])
        await database.interviews.create_index([("user_id", 1), ("created_at", -1)])
        await database.resumes.create_index("created_at")
        await database.jobs.create_index("created_at")
        await database.analyses.create_index("resume_id")
        await database.interviews.create_index("created_at")
        print("MongoDB connected")
    except Exception as exc:
        print(f"MongoDB connection/index warning: {exc}")

async def close_mongo_connection():
    global client
    if client:
        await client.close()

def get_database():
    if database is None:
        raise RuntimeError("Database is not initialized")
    return database
