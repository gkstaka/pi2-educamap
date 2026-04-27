# NOTE: SQLAlchemy --> Cada classe é uma tabela no SQL.
# TODO: Pensar o desenho do banco de dados.

import os
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Escola(Base):
    __tablename__ = 'escolas'
    id_escola = Column(Integer, primary_key=True)
    nome_escola = Column(String(255))
    endereco = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)
    tipo_rede = Column(String(50))
    localizacao = Column(String(50))
    porte_escola = Column(String(100))
    capacity_weight = Column(Float) # FIX: ver a localização deste item.


# A string de conexão usará as variáveis que definiremos no Docker
DB_URL = os.getenv("DATABASE_URL", "postgresql://admin_educa:senha_projeto@db:5432/educamap_db")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#linha adcionada para o sistema esperar o banco de dados - Ufa!!!
Base.metadata.create_all(bind=engine)
