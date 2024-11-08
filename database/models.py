from sqlalchemy import Column, Integer, String, ForeignKey, SmallInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class RegionTabla(Base):
    __tablename__ = "regiones"

    idregion = Column(Integer, primary_key=True)
    nombre = Column(String(25), nullable=False)
    active = Column(SmallInteger, nullable=False, default=1)
    url = Column(String, nullable=True, default=None)


class ComunaTabla(Base):
    __tablename__ = "comunas"

    idcomuna = Column(Integer, primary_key=True)
    idregion = Column(Integer, ForeignKey("regiones.idregion"), nullable=False)
    nombre = Column(String(25), nullable=False)
    active = Column(SmallInteger, nullable=False, default=1)
    url = Column(String, nullable=True, default=None)

    regiones = relationship("RegionTabla")
