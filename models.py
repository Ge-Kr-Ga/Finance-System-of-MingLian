from sqlalchemy import create_engine, Column, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Record(Base):
    __tablename__ = 'records'
    
    id = Column(String, primary_key=True)
    name = Column(String)
    department = Column(String)
    item = Column(String)
    amount = Column(Float)
    pdf_path = Column(Text)
    remarks = Column(Text)
    category = Column(String)

# 创建数据库引擎
engine = create_engine('sqlite:///ZZBNJZ_records.db')
Base.metadata.create_all(engine)

# 创建会话
Session = sessionmaker(bind=engine)