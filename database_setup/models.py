from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database_setup.connections import Base


# ─── User Model ──────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id        : Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name      : Mapped[str]           = mapped_column(String(100), nullable=False)
    email     : Mapped[str]           = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
    DateTime, default=lambda: datetime.now(timezone.utc))
    phone : Mapped[str] = mapped_column(String(20), nullable=False)
    test_column:Mapped[str]=mapped_column(String(20),nullable=True)
    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[list["Feedback"]] = relationship(
        "Feedback", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_users_email", "email"),
    )

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"


# ─── Conversation Model ───────────────────────────────────────────────────────
class Conversation(Base):
    __tablename__ = "conversations"

    id        : Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id   : Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role      : Mapped[str]      = mapped_column(String(20), nullable=False)   # 'user' ya 'assistant'
    message   : Mapped[str]      = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="conversations")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="chk_role"),
        Index("idx_conversations_user_created", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<Conversation id={self.id} user_id={self.user_id} role={self.role}>"


# ─── Feedback Model ───────────────────────────────────────────────────────────
class Feedback(Base):
    __tablename__ = "feedback"

    id          : Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id     : Mapped[int]           = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user_message: Mapped[str]           = mapped_column(Text, nullable=False)
    bot_response: Mapped[str]           = mapped_column(Text, nullable=False)
    rating      : Mapped[str]           = mapped_column(String(20), nullable=False)  # 'thumbs_up' / 'thumbs_down'
    created_at  : Mapped[datetime]      = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="feedbacks")

    __table_args__ = (
        CheckConstraint("rating IN ('thumbs_up', 'thumbs_down')", name="chk_rating"),
        Index("idx_feedback_user", "user_id"),
        Index("idx_feedback_rating", "rating"),
    )

    def __repr__(self):
        return f"<Feedback id={self.id} user_id={self.user_id} rating={self.rating}>"