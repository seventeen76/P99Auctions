import re
import sqlite3
import ConfigParser
import os
import time
from time import strftime
from datetime import datetime
from time import strptime
from time import sleep
import hashlib
import sys

# Log file class
class Log:
	def __init__(self, path):
		self.path = path
		self.name = self.path[path.rfind('\\')+1:]
		self.file = open(self.path)
		self.contents = self.file.read()
		self.file.close()
		if len(self.contents) > 5:
			self.hash = hashlib.md5(self.contents).hexdigest()
		else:
			self.hash = 0

	def AuctionLines(self):
		return re.findall('.*\] [A-Z][a-z]* auctions\,.*', self.contents)

	def NumberOfAuctions(self):
		return len(re.findall('\] [A-Z][a-z]* auctions\,',self.contents))

	def Logged(self, current):
		if current == True:
			log_hash = self.CurrentHash()
		else:
			log_hash = self.hash
		log_db = Database('auctions.db')
		log_db.cur.execute("SELECT count(*) FROM logs WHERE name = '" + self.name + "'")
		log_db_count = log_db.cur.fetchone()
		if int(log_db_count[0]) < 1:
			log_db.cur.execute("INSERT INTO logs VALUES ('" + self.name + "','" + log_hash + "')")
		else:
			log_db.cur.execute("UPDATE logs SET name = '" + self.name + "', hash = '" + log_hash + "'")
		log_db.conn.commit()
		log_db.conn.close()

	def IsLogged(self):
		log_db = Database('auctions.db')
		log_db.cur.execute("SELECT hash FROM logs WHERE name = '" + self.name + "'")
		log_db_hash = log_db.cur.fetchone()
		if self.name == 'dbg.txt':
			return True
		if log_db_hash == None:
			return False
		if log_db_hash[0] == self.hash:
			return True
		else:
			return False

	def CurrentHash(self):
		self.file = open(self.path)
		contents = self.file.read()
		self.file.close()
		if len(contents) > 5:
			hashcalc = hashlib.md5(contents).hexdigest()
		else:
			hashcalc = 0
		return hashcalc

	def IsUpdated(self):
		if self.name == 'dbg.txt':
			return False
		self.file = open(self.path)
		contents = self.file.read()
		self.file.close()
		if len(contents) > 5:
			hashcalc = hashlib.md5(contents).hexdigest()
		else:
			hashcalc = 0
		if hashcalc == self.hash:
			return False
		else:
			return True

	def FollowAuctions(self):
		f = open(self.path)
		f.seek(0,2)
		while True:
			line = f.readline()
			if not line:
				time.sleep(0.1)    # Sleep briefly
				continue
			out = re.findall('.*\] [A-Z][a-z]* auctions\,.*', line)
			if len(out) > 0:
				yield out[0]

# P99Auctions configuration class
class Config:
	def __init__(self, configfile):
		self.config = ConfigParser.RawConfigParser()
		self.config.read(configfile)
		if not self.config.has_section('Basic'):
			self.config.add_section('Basic')
		if self.config.has_option('Basic', 'eqpath'):
			self.eqpath = self.config.get('Basic', 'eqpath')
			self.CheckLogs()
		else:
			print "No eqpath found in " + configfile
			self.eqpath = raw_input("What is the path to your EQ install? ")
			self.CheckLogs()
			self.config.set('Basic','eqpath', self.eqpath)
		with open(configfile, 'wb') as f:
			self.config.write(f)

	def CheckLogs(self):
		if os.path.isdir(self.eqpath + '\Logs'):
			self.logs = self.eqpath + '\Logs'
		else:
			print "No Logs directory found in EQ path."
			exit()

# P99Auctions database class
class Database:
	def __init__(self,db):
		self.conn = sqlite3.connect(db)
		self.cur = self.conn.cursor()

	def insert(self,auction):
		for item in auction.items:
			self.cur.execute("SELECT count(*) FROM auctions WHERE auctioneer = '" + auction.auctioneer + "' AND time = '" + auction.time + "' AND item = '" + item[0] + "'")
			auc_count = self.cur.fetchone()
			if int(auc_count[0]) < 1:
				try:
					self.cur.execute("INSERT INTO auctions VALUES (?,?,?,?,?)", (auction.time, auction.auctioneer, item[2], item[0], item[1]))
					self.conn.commit()
				except sqlite3.OperationalError:
					print sys.exc_info()
					print("DATABASE LOCKED; sleeping for 3 seconds and trying again")
					time.sleep(3)
					Retry

# Auction class, one auction message
class Auction:
	def __init__(self,auction):
		self.time = auction.split(']')[0][1:]
		self.time = datetime.strptime(self.time, '%a %b %d %H:%M:%S %Y').strftime('%Y-%m-%d %H:%M:%S')
		self.text = auction.split(' auctions, ')[1]
		self.auctioneer = auction.split(' auctions, ')[0].split(']')[1][1:]
		self.wts = self.WTSBool(self.text)
		self.wtb = self.WTBBool(self.text)
		self.item_db = Items('items.db')
		if self.wts:
			self.wts_items = self.GetItems('wts',self.text)
		else:
			self.wts_items = []
		if self.wtb:
			self.wtb_items = self.GetItems('wtb',self.text)
		else:
			self.wtb_items = []
		self.items = self.wtb_items + self.wts_items
		print self.time + " " + self.auctioneer + ":"
		for item in self.items:
			print item[2] + " " + item[0] + " " + item[1]

	def WTSBool(self,text):
		if "wts" in text.lower():
			return True
		if "wts" not in text.lower() and "wtb" not in text.lower():
			return True
		return False

	def WTBBool(self,text):
		if "wtb" in text.lower():
			return True
		return False

	def insert_array(self):
		auction_insert = []
		for item in self.items:
			auction_insert.append((self.time,self.auctioneer,item[2],item[0],item[1]))
		return auction_insert

	def GetItems(self,auction_type,text):
		text = text.lower()
		for number in range(0,10):
			text = text.replace('.' + str(number) + 'k',str(number) + '00 ')
		for number in range(0,10):
			text = text.replace(str(number) + 'k',str(number) + '000 ')
		text = text.replace('.','')
		text = re.sub('[^A-Z^a-z^ ^0-9^]',' ',text)
		ReturnItems = []
		if auction_type == "wts":
			opposite_type = "wtb"
		else:
			opposite_type = "wts"
		for item in self.item_db.items:
			item_name = item.split('|')[1].lower()
			item_name = re.sub('[^A-Z^a-z^ ^0-9^]', ' ', item_name)
			if item_name in text:
				#print "Found " + item_name + " in text."
				auction_type_position = text.lower().rfind(auction_type)
				opposite_type_position = text.lower().rfind(opposite_type)
				item_position = text.lower().rfind(item_name)
				# If there is a number after the item
				price_string = text[item_position + len(item_name):]
				next_item_pos = re.search('[A-Za-z][A-Za-z]', price_string)
				if next_item_pos:
					price_string = price_string[:next_item_pos.start()]
				if price_string[0:1] == " ":
					price = price_string[1:]
				else:
					price = price_string
				if " " in price:
					pp_found = 0
					prices = price.split(" ")
					for pprice in prices:
						if "p" in pprice:
							price = re.sub('[^0-9]','',pprice)
							pp_found = 1
					if pp_found == 0:
						price = re.sub('[^0-9]','',prices[0])
				if len(price) < 1:
					price = '0'
				if opposite_type_position < 0:
						ReturnItems.append((item_name,price,auction_type))
				else:
					if item_position > auction_type_position and opposite_type_position < auction_type_position:
						ReturnItems.append((item_name,price,auction_type))
					if item_position > auction_type_position and opposite_type_position > auction_type_position and item_position < opposite_type_position:
						ReturnItems.append((item_name,price,auction_type))
				text = text.replace(item_name + price_string, '')
		return ReturnItems

# Items database class
class Items:
	def __init__(self,itemdb):
		self.items = []
		with open(itemdb) as f:
			for line in f:
				self.items.append(line)