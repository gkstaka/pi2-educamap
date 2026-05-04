# NOTE: SQLAlchemy --> Cada classe é uma tabela no SQL.
# TODO: Pensar o desenho do banco de dados.

import os
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
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
    capacity_weight = Column(Float)

    resultados = relationship("Resultado", back_populates="resultados")


class Resultado(Base):
    __tablename__ = 'resultados'
    id_resultado = Column(Integer, primary_key=True, autoincrement=True)

    #Chave estrangeira relacionada à escolas
    id_escola = Column(Integer, ForeignKey('escolas.id_escola'), nullable=False)

    raio_calculado = Column(Float)
    capacidade_matricula = Column(Float)

    escola = relationship("Escola", back_populates="escolas")


# A string de conexão usará as variáveis que definiremos no Docker
DB_URL = os.getenv("DATABASE_URL", "postgresql://admin_educa:senha_projeto@db:5432/educamap_db")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#linha adcionada para o sistema esperar o banco de dados - Ufa!!!
Base.metadata.create_all(bind=engine)


# TODO: fazer que os dados do campo :
# raio_calculado --> get_calculated_radius() -> data_utils
# capacidade_matricula --> extract_maximum_capacity_weight -> data_utils
