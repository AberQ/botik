from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


DATABASE_URL = "sqlite:///./test.db"

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)  
    artikul = Column(Integer, unique=True, index=True, nullable=False) 
    name = Column(String, nullable=False)  
    sale_price = Column(Float) 
    rating = Column(Float) 
    quantity = Column(Integer) 
 