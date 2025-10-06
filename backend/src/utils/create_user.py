from uuid import uuid4
from ..infrastructure.database import Database
from ..infrastructure.repositories import SQLUserRepository
from ..infrastructure.services import BcryptPasswordService
from ..domain.entities import User
from ..infrastructure.config import settings


def create_test_user():
    if not settings.database_url:
        print("DATABASE_URL not configured")
        return
    
    db = Database(settings.database_url)
    db.create_tables()
    
    user_repository = SQLUserRepository(db.get_session())
    password_service = BcryptPasswordService()
    
    test_user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        hashed_password=password_service.hash_password("password123"),
        is_active=True,
        is_verified=True
    )
    
    try:
        user_repository.create(test_user)
        print(f"Test user created successfully:")
        print(f"Email: {test_user.email}")
        print(f"Username: {test_user.username}")
        print(f"Password: password123")
    except Exception as e:
        print(f"Error creating user: {e}")


if __name__ == "__main__":
    create_test_user()
