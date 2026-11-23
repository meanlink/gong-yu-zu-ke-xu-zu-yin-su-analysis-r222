import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rental_app:rental_pass@db:5432/rental_ops")
JWT_SECRET = os.getenv("JWT_SECRET", "gb1059-rental-secret")
JWT_ALGORITHM = "HS256"
