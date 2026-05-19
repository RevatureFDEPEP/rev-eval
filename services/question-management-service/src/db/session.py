from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from src.config.settings import settings
from src.models.question import Question

# Global MongoDB client and database
client: AsyncMongoClient = None
db = None


async def init_db():
    """
    Initialize MongoDB connection with proper error handling.

    This function:
    - Creates a MongoDB client with connection pooling
    - Verifies the connection with a ping
    - Initializes Beanie ODM for document models
    - Properly assigns to global variables

    Raises:
        ConnectionFailure: If unable to connect to MongoDB
        ServerSelectionTimeoutError: If MongoDB server is unreachable
    """
    global client, db

    try:
        print(f"🔄 Connecting to MongoDB at {settings.MONGO_CLUSTER}...")

        # Create MongoDB async client with connection settings
        client = AsyncMongoClient(
            settings.mongo_url,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=10000,  # 10 second connection timeout
            socketTimeoutMS=10000,  # 10 second socket timeout
            maxPoolSize=10,  # Connection pool size
            minPoolSize=1,
            retryWrites=True,
            retryReads=True
        )

        # Get database instance
        db = client[settings.MONGO_DB]

        # Test the connection with ping
        await client.admin.command('ping')
        print(f"✅ Successfully connected to MongoDB: {settings.MONGO_DB}")

        # Initialize Beanie ODM
        await init_beanie(database=db, document_models=[Question])
        print(f"✅ Beanie ODM initialized with Question model")

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        print(f"   Cluster: {settings.MONGO_CLUSTER}")
        print(f"   Database: {settings.MONGO_DB}")
        print(f"   User: {settings.MONGO_USER}")
        raise

    except Exception as e:
        print(f"❌ Unexpected error during MongoDB initialization: {e}")
        import traceback
        traceback.print_exc()
        raise


async def close_db():
    """
    Close MongoDB connection gracefully.

    This should be called during application shutdown to ensure
    all connections are properly closed and resources are released.
    """
    global client
    if client:
        client.close()
        print("✅ MongoDB connection closed")


async def get_database():
    """
    Get the MongoDB database instance.

    Returns:
        Database: The MongoDB database instance

    Raises:
        RuntimeError: If database is not initialized (init_db not called)
    """
    if db is None:
        raise RuntimeError(
            "Database not initialized. Call init_db() during application startup."
        )
    return db


async def get_client():
    """
    Get the MongoDB client instance.

    Returns:
        AsyncMongoClient: The MongoDB client instance

    Raises:
        RuntimeError: If client is not initialized
    """
    if client is None:
        raise RuntimeError(
            "MongoDB client not initialized. Call init_db() during application startup."
        )
    return client


async def check_connection():
    """
    Check if MongoDB connection is alive.

    Returns:
        bool: True if connection is alive, False otherwise
    """
    global client
    if client is None:
        return False

    try:
        await client.admin.command('ping')
        return True
    except Exception as e:
        print(f"⚠️ MongoDB connection check failed: {e}")
        return False