#!/usr/bin/env

import os, logging, ConfigParser, zulip, models
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker, exc

class Message(object):
	"""a Zulip message object"""

	def __init__(self, mtype, content, to, subject):
		self.type = mtype
		self.content = content
		self.to = to
		self.subject = subject

	@property
	def data(self):
		return {
			"type": self.type,
			"content": self.content,
			"subject": self.subject,
			"to": self.to,
		}

class GenderBot(object):
	def __init__(self, client, uri):
		self.client = client
		self.uri = uri
		self.initDB(models.Base)
		self.commands = {
			"get": self.getPronouns,
			"set": self.setPronouns,
			"invite": self.invite,
			"add": self.addPronouns,
			"delete": self.deletePronouns,
			"prefer": self.preferPronouns,
			"welcome": self.welcome
		}

	def initDB(self, dBaseClass):
		self.engine = create_engine(self.uri)
		dBaseClass.metadata.create_all(self.engine)
		self.session = sessionmaker(bind=self.engine)()

	def run(self):
		"""run the GenderBot presumably forever (blocking)"""
		print ("GenderBot is running")
		self.client.call_on_each_message(self.respondToMessage)

	def respondToMessage(self, msg):
		try:
			sender = msg["sender_email"]
			content = msg["content"]
			print ("Received new message from {0}: {1}".format(sender, content))

			if sender != self.client.email: #prevent bot from talking to itself
				response = self.parseMessageContent(msg["content"], msg["sender_email"], self.commands)
				m = Message("private", response, sender, "")
				self.client.send_message(m.data)

		except Exception as e:
			logging.exception(e)

	def parseMessageContent(self, content, sender, commandSet):
		
		if not len(content):
			return "Error: message is empty"

		#seperate command from args by first space
		commandEnd = content.find(" ")
		if commandEnd >= 0:
			command = content[:commandEnd]
			argstring = content[commandEnd+1:]
		#if no space, there are no args
		else:
			command = content
			argstring = ""

		f = commandSet.get(command)
		if f == None:
			print ("Command in message not recognized")
			return self.unrecognized(sender)
		else:
			print ("Command in message: " + command)
			return f(argstring, sender)

	def getPronouns(self, argstring, sender):
		if argstring == "":
			email = sender
		else:
			email = argstring

		if email == sender:
			prefixes = ("You have", "Your")
			suffix = "To set your pronouns, use the `set` command."
		else:
			prefixes = ("This user has", "This user's")
			suffix = "You may invite this user by entering `invite " + email + "`."
		try:
			users, pronouns = zip(*self.session.query(models.User, models.UserPronounSet)\
				.filter(models.User.id==models.UserPronounSet.user_id)\
				.filter(models.User.email==email)\
				.all())
		#if no records are found, we will get a ValueError for the unpack
		except ValueError:
		#if not len(pronouns):
			return prefixes[0] + " not set any pronouns. " + suffix

		pronounStrings = [(' (preferred)'*p.preferred) + ': "{}", "{}", "{}", "{}", and "{}"'.format(
			p.p_nominative,
			p.p_oblique,
			p.p_possessive,
			p.p_possessive_determiner,
			p.p_reflexive) for p in pronouns]
		if len(pronounStrings) == 1:
			fullString = prefixes[1] + " pronouns are " + pronounStrings[0]
		else:
			fullString = prefixes[1] + " pronouns are:\n" + "\n".join(
				[str(i) + p for i, p in enumerate(pronounStrings)])
		return fullString 

	def setPronouns(self, argstring, sender):
		usage = "Usage:\n"\
			"`set [INDEX] <nominative>, <oblique>, <determiner>, <possessive>, <reflexive>`\n"\
			"Example: `set they, them, their, theirs, themselves`\n"\
			"INDEX is only required if you have added more than one pronoun set."
		args = argstring.split(", ")
		if argstring in ["", "--help"]:
			return usage
		#check if pronoun_set index is specified
		elif args[0][0].isdigit():
			try:
				#try to split index from first pronoun arg
				seploc = args[0].index(" ") #throws ValueError if none
				index = args[0][:seploc]
				args[0] = args[0][seploc+1:]
			except ValueError:
				#mark index as invalid/unspecified (index normally starts at 1)
				index = 0
		user = self.getUser(sender, True)
		pronounSets = self.getUserPronounSets(user.id) #will be in order of user_id
		l = len(pronounSets)
		if l <= 1:
			ps = models.UserPronounSet(
				user.id, False,1,args[0],args[1],args[2],args[3],args[4]
			)
			if l:
				pronounSets[0] = ps
			else:
				self.session.add(ps)
			self.session.commit()
		else:
			pass

		return self.getPronouns("", sender)

	def invite(self, argstring, sender):
		invitee = argstring
		if sendInvitation(invitee):
			return "You have successfully invited **" + invitee + "**."
		else:
			return "This user has already been invited."

	def sendInvitation(self, argstring):
		"""send invitation to user, return True if success"""

		return True

	def addPronouns(self, argstring, sender):
		return 1

	def deletePronouns(self, argstring, sender):
		return 1

	def preferPronouns(self, argstring, sender):
		return 1

	def unrecognized(self, sender):
		user = self.getUser(sender)
		#determine whether user exists and has been welcomed
		if user:
			welcomed = user.welcomed
		else:
			welcomed = False

		#if user has not been welcomed, return welcome message
		#if user doesn't exist, also create user
		if not welcomed:
			return self.welcome("", sender, user)
		else:
			return self.returnGenericMessage(sender)

	def welcome(self, argstring, sender, user=None):
		"""
		send welcome message to user and set user.welcomed to True
		"""

		if not user:
			user = getUser(sender)
		user.welcomed = True
		self.session.commit()

		msg = "Hello! I am a robot that can store your preferred gendered pronouns."
		return "\n".join([msg, self.returnGenericMessage(sender)])

	def returnGenericMessage(self, sender):
		#return "Valid commands are **get**, **set**, **add**, **prefer**, **delete**, and **invite**.\n"\
		return "Valid commands are **get** and **set**.\n"\
			"To learn more about a command, enter `<commandname> --help`"

	def getUser(self, email, addIfNone=False):
		"""get user by email; add record if user not found and addIfNone is True"""

		try:
			return self.session.query(models.User).filter_by(email=email).one()
		except exc.NoResultFound:
			if addIfNone:
				return self.addUser(email, True, False)

	def addUser(self, email, welcomed, invited):
		user = models.User(email, welcomed, invited)
		try:
			self.session.add(user)
			self.session.commit()
			return user
		except exc.IntegrityError:
			self.session.rollback()

	def getUserPronounSets(self, user_id, sort=1):
		q = self.session.query(models.UserPronounSet).filter_by(user_id=user_id)
		if sort == 1:
			q = q.order_by(models.UserPronounSet.user_id)
		return q.all()

	#def markUserAsWelcomed(self, email)

def loadConfig(*fnames):
	"""
	load one or more config files in descending order of precedence
	(duplicate values between files will be overridden by the last file)
	"""

	config = ConfigParser.ConfigParser()
	if not config.read(fnames):
		raise IOError(str(fnames) + " not found")
	else:
		return config

def configSectionVals(fname, fallback, section, options):
	"""
	return a dict of values from a section of a config file

	arguments:
	fname -- default config file name
	fallback -- backup config file name
	section -- section name
	options -- list of options to search for in section
	"""

	config = loadConfig(fallback, fname)
	vals = {}
	for op in options:
		vals[op] = config.get(section, op).strip('"')
	return vals

def makeApplicationBot():
	cfg = "config.ini"
	fallback = os.path.join(os.path.expanduser("~"), ".zuliprc")
	try:
		dbConfig = configSectionVals(cfg, fallback, "database", ["uri"])
		apiConfig = configSectionVals(cfg, fallback, "api", ["key", "email"])
	except (ConfigParser.NoSectionError or ConfigParser.NoOptionError) as e:
		print ("Config file error: " + str(e))
		return
	except Exception as e:
		print ("Error: " + str(e))
		return
	
	return GenderBot(
		zulip.Client(email=apiConfig["email"], api_key=apiConfig["key"]),
		dbConfig["uri"]
	)

def main():
	bot = makeApplicationBot()
	bot.run()

if __name__ == "__main__":
	main()

#client = zulip.Client()
#m = Message("private", "good morning from deckybot", "cosstropolis@gmail.com", "")
#client.send_message(m.data)
