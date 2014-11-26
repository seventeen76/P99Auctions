#	 This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


from p99auctions import Log
from p99auctions import Config
from p99auctions import Database
from p99auctions import Auction
import os
import sys
from multiprocessing import Pool
import time
import winsound

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
def process_auction(auction_line,alerts_enabled=False,beeps=False):
	auctions_db = Database('auctions.db')
	auction = Auction(auction_line)
	auctions_db.insert(auction)
	if alerts_enabled:
		alerts = auction.Alerts(auctions_db)
		if alerts:
			for alert in alerts:
				if beeps:
					winsound.Beep(2600,300)
				print "(I" + alert[4] + " M" + alert[5] + ") " + alert[0] + " : " + alert[1] + " @ " + alert[2] + " : " + alert[3]

# Main loop for every log file
if __name__ == '__main__':

	# Functionality to specify active or passive logging only
	activeonly = False
	passiveonly = False
	for arg in sys.argv:
		if arg == "--active-only":
			activeonly = True
		if arg == "--passive-only":
			passiveonly = True
	if activeonly and passiveonly:
		print "You can not specify active only and passive only options together."
		exit()

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
	if not activeonly:
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
	if not passiveonly:
		print "[Identifying Active Log]"
		while True:
			try:
				print "Sleeping 3 seconds to allow logging..."
				time.sleep(3)
				# Build a list of logs which changed, set the active log
				active_logs = []
				for log in logs:
					if log.IsUpdated():
						print log.name + " is active."
						active_logs.append(log)
				active_log = active_logs[0]
				break
			except:
				print "No log found..."
		# Watch the active log, process auctions, and stamp the current md5 in logs table
		for line in active_log.FollowAuctions():
			process_auction(line,True)
			active_log.Logged(current=True)