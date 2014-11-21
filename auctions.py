from p99auctions import Log
from p99auctions import Config
from p99auctions import Database
from p99auctions import Auction
import os
from multiprocessing import Pool
import time

# Append a Log object to logs for every .txt file in the EQ logs path
def read_logs(path):
	print "[Finding Logs]"
	logs = []
	for file in os.listdir(path):
		if ".txt" in file:
			logs.append(Log(path + '\\' + file))
	print "Found " + str(len(logs)) + " potential log files."
	return logs

# Process auction line and insert to database
def process_auction(auction_line):
	auctions_db = Database('auctions.db')
	auction = Auction(auction_line) 
	auctions_db.insert(auction)

# Main loop for every log file
if __name__ == '__main__':

	# Get config variables
	print "\n[P99Auctions]\n"
	print "[Reading Config]"
	p99auctions_cfg = Config('p99config.cfg')

	# Initalize some things
	p = Pool()
	total_auctions = 0

	# Initalize database and get a list of log files
	auctions_db = Database('auctions.db')
	logs = read_logs(p99auctions_cfg.logs)

	# For every log
	for log in logs:
		# If log md5 matches database logs table md5 for this filename, skip
		if log.IsLogged():
			print "[Analyzed Log] - " + log.name
			continue
		# Processing log since md5 doesn't match logs table
		print "[Analyzing Log] - " + log.name
		print "Found " + str(log.NumberOfAuctions()) + " auction lines."
		print "[Parsing & Inserting Auctions]"
		total_auctions += log.NumberOfAuctions()
		print "Total auctions: " + str(total_auctions)
		# Multiprocessing of log auction lines
		p.map(process_auction, log.AuctionLines())
		# Stamp log md5 into logs table in database, use original md5 not current md5
		log.Logged(current=False)

	# Determine which log is actively being logged to
	print "[Identifying Active Log]"
	print "Sleeping 10 seconds to allow logging..."
	time.sleep(10)
	# Build a list of logs which changed, set the active log
	active_logs = []
	for log in logs:
		if log.IsUpdated():
			print log.name + " is active."
			active_logs.append(log)
	active_log = active_logs[0]
	# Watch the active log, process auctions, and stamp the current md5 in logs table
	for line in active_log.FollowAuctions():
		print line
		process_auction(line)
		active_log.Logged(current=True)