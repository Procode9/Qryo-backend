from sqlalchemy import Integer

class User(Base):
    __tablename__ = "users"

    api_key: Mapped[str] = mapped_column(String, primary_key=True)
    credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
