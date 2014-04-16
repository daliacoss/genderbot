#!/usr/bin/env

from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
	__tablename__ = 'users'
	id = Column(Integer, primary_key=True)
	email = Column(String, unique=True, index=True)
	welcomed = Column(Boolean)
	invited = Column(Boolean)

	def __init__(self, email, welcomed=False, invited=False):
		self.email = email
		self.welcomed = welcomed
		self.invited = invited

class UserPronounSet(Base):
	__tablename__ = 'user_pronoun_sets'
	id = Column(Integer, primary_key=True)
	user_id = Column(Integer, ForeignKey("users.id"))
	preferred = Column(Boolean)
	p_nominative = Column(String(50))
	p_oblique = Column(String(50))
	p_possessive = Column(String(50))
	p_possessive_determiner = Column(String(50))
	p_reflective = Column(String(50))\

	def __init__(self, user_id,
		preferred,
		p_nominative,
		p_oblique,
		p_possessive,
		p_possessive_determiner,
		p_reflective
	):
		self.user_id = user_id
		self.preferred = preferred
		self.p_nominative = p_nominative
		self.p_oblique = p_oblique
		self.p_possessive = p_possessive
		self.p_possessive_determiner = p_possessive_determiner
		self.p_reflective = p_reflective