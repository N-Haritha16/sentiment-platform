from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Sentiment(Base):
    __tablename__ = "sentiments"
    id = Column(Integer, primary_key=True)
    text = Column(String)
    sentiment = Column(String)
