from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


SQLALCHEMY_DATABASE_URL = "mysql://admin:password@127.0.0.1/copy"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

Session = sessionmaker(engine)
session = Session()
