import os

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import inspect, text


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./backyardos.db"
)

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
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
    # create_all does not alter existing tables. Legacy rows belong to Probe 1.
    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("sensorreading")}
        if "probe_id" not in columns:
            connection.execute(text(
                "ALTER TABLE sensorreading ADD COLUMN "
                + ("IF NOT EXISTS " if connection.dialect.name == "postgresql" else "")
                + "probe_id INTEGER NOT NULL DEFAULT 1"
            ))


def get_session():
    with Session(engine) as session:
        yield session