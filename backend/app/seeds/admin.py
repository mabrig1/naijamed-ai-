"""Seed a default admin user if no admin exists."""
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.user import User, UserRole


ADMIN_EMAIL = "admin@nigerflora.com"
ADMIN_PASSWORD = "NigerFlora@Admin2026!"


def seed_admin(db: Session) -> None:
    exists = db.query(User).filter(User.role == UserRole.admin).first()
    if exists:
        return
    admin = User(
        email=ADMIN_EMAIL,
        full_name="NigerFlora Admin",
        password_hash=hash_password(ADMIN_PASSWORD),
        role=UserRole.admin,
        is_active=True,
    )
    db.add(admin)
    db.commit()
