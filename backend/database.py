import os

from sqlmodel import SQLModel, create_engine, Session


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./backyardos.db"
)

connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session