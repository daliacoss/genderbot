#!/usr/bin/env 

import os, ConfigParser, zulip, sqlalchemy

class Message(object):
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
	commands = {
		"get": getPronouns,
		"set": setPronouns,
		"invite": invite,
		"add": addPronouns,
		"delete": deletePronouns,
		"prefer": preferPronouns
	}

	def __init__(self, client, uri):
		self.client = client
		self.uri = uri

	def run(self):
		"""run the GenderBot presumably forever (blocking)"""

		self.client.call_on_each_message(self.respondToMessage)

	def respondToMessage(self, msg):
		response = parseMessageContent(msg["content"], msg["sender_email"], self.commands)
		m = Message("private", response, msg["sender_email"], "")
		self.client.send_message(m.data)

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

		return commandSet[command](argstring, sender)

	def getPronouns(self, argstring, sender):
		if argstring == "":
			user = sender
		else:
			user = argstring

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
		vals[op] = config.get(section, op)
	return vals

def main():
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
	
	bot = GenderBot(
		zulip.Client(email=apiConfig["email"], api_key=apiConfig["key"]),
		dbConfig["uri"]
	)
	bot.run()

if __name__ == "__main__":
	main()

#client = zulip.Client()
#m = Message("private", "good morning from deckybot", "cosstropolis@gmail.com", "")
#client.send_message(m.data)
