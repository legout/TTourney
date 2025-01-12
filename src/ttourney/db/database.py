from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

def get_db_connection(db_url: str = "sqlite:///:memory:"):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
