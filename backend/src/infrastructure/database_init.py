from .database import Database
from .config import settings


def init_database():
    if not settings.database_url:
        raise ValueError("DATABASE_URL not configured")
    
    db = Database(settings.database_url)
    db.create_tables()
    print("Database tables created successfully")


if __name__ == "__main__":
    init_database()
