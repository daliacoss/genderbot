from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
	__tablename__ = 'users'
	id = Column(Integer, primary_key=True)
	email = Column(String)
	welcomed = Column(Boolean)
	invited = Column(Boolean)

class UserPronounSet(Base):
	__tablename__ = 'user_pronoun_sets'
	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"))
	is_preferred = Column(Boolean)
	nominative = Column(String(50))
	oblique = Column(String(50))
	possessive = Column(String(50))
	possess_determiner = Column(String(50))
	reflective = Column(String(50))
