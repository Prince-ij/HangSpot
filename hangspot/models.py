import os

from flask_login import UserMixin
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)

base_url = os.path.abspath(os.path.dirname(__file__))

meta = MetaData()
database = create_engine(f"sqlite:///{os.path.join(base_url, 'data.db')}")
db = database.connect()

users = Table(
    "users",
    meta,
    Column("id", Integer, primary_key=True),
    Column("username", String, unique=True),
    Column("password", String),
    Column("email", String, nullable=False, unique=True),
)

wifi_updates = Table(
    "wifi_updates",
    meta,
    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("address", String),
    Column("opening_time", String),
    Column("closing_time", String),
    Column("wifi_strength", Integer),
    Column("available_days", String),
    Column("description", String),
    Column("image", String),
    Column("user_id", ForeignKey("users.id")),
)

hangout_updates = Table(
    "hangout_updates",
    meta,
    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("address", String),
    Column("opening_time", String),
    Column("closing_time", String),
    Column("description", String),
    Column("available_days", String),
    Column("image", String),
    Column("user_id", ForeignKey("users.id")),
)

user_liked_post = Table(
    "user_liked_post",
    meta,
    Column("user_id", ForeignKey("users.id")),
    Column("wifi_update_id", Integer),
    Column("hangout_update_id", Integer),
)

likes = Table(
    "likes",
    meta,
    Column("id", Integer, primary_key=True),
    Column("user_id", ForeignKey("users.id")),
    Column("hangout_id", ForeignKey("hangout_updates.id")),
    Column("wifi_id", ForeignKey("wifi_updates.id")),
)
meta.create_all(database)


class User(UserMixin):
    def __init__(self, user_row):
        self.id = user_row.id
        self.username = user_row.username
        self.email = user_row.email
        self.password = user_row.password

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return True
