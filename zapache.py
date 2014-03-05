#!/usr/bin/python

# Zabbix Apache probe
# Gcharot 27/14 V1.1

# TODO : Create lock file to avoid multiple instance running at the same time


import apachelogs
import re
import sys
import os
from subprocess import call


##### FUNCTION's DECLARATIONS #####

# Count number of HTTP response code defined in my_resp_code
def count_response_code(response_code):
	for code in my_resp_code:
		if response_code == code:
			stats[response_code] += 1

# Count number of HTTP request type defined in my_req_type
def count_request_type(http_resquest):
	request_type=re.match(r'^(\w+) ', log_line.request_line, re.I)
	for rtype in my_req_type:
		if request_type.group(1) == rtype:
			stats[rtype] +=1
			break

# Launch logtail on apache logfile
def logtail_that_file():
	if debug == 1:
		print "Logtailing file ", logfile, "with offset ", logtail_offset, "sending delta to ", logtail_file

	TAILFILE = open(logtail_file, 'w')
	
	try:
	 	call(["logtail2", "-f", logfile, "-o", logtail_offset], stdout=TAILFILE)		# Call logtail2 & redirect output to logtail_file
	except OSError as detail:
  		print "Something went wrong while exectuting logtail2 : ", detail

  	TAILFILE.close()

# Zend values to zabbix via zabbix_sender
def zabbix_send(metric, value):
	key = zabbix_key + "[" + metric + "]"					# Generate zabbix key => zabbix_key[metric]
	if debug == 1:
		print "sending key : ", key, " - value : ", value

	if send_to_zabbix > 0:
		try:
		  	call([zabbix_sender, "-c", zabbix_conf, "-k", key, "-o", str(value)], stdout=FNULL, stderr=FNULL)		# Call zabbix_sender
		except OSError as detail:
  			print "Something went wrong while exectuting zabbix_sender : ", detail

###########

# Check argv
try:
	logfile = sys.argv[1]
	if not os.path.isfile(logfile):
		print logfile, " : invalid filename"
		exit(1)
except:
	print "Script requires an apache logfile path as argument"
	exit(1)


##### User defined variables

# Zabbix
zabbix_sender = "/usr/bin/zabbix_sender"			# Path to zabbix_sender binary
zabbix_conf = "/etc/zabbix/zabbix_agentd.conf"		# Path to Zabbix agent configuration
zabbix_key = "apache"								# Zabbix item's base key

# Logtail
logtail_offset ="/tmp/zapache-logtail.offset"		# Logtail offset. CHANGE ME if you're running multiple instances of zapache
logtail_file = "/tmp/zapache-logtail.data"

# Zapache
debug = 1 											# Debug : 0 = Off
send_to_zabbix = 0 									# Send data to zabbix ? > 0 = Yes / 0 = No
my_resp_code = ("200", "401", "402", "403", "404", "405", "406", "408", "409", "410", "411", "412", "413", "414", "417", "500", "501", "502", "503", "504")				# Wanted status code.
my_req_type = ("GET", "POST")																																			# Wanted request type


#####

##### Global variable init	

stats = {			# Put results in this dictionary - Initialize to 0
"nr_req":0, 		# Total number of requests
"ip_count":0,		# Number of client's IP
}

for code in my_resp_code:														# Initialize stats dictionary to 0 based on user wanted status code (my_resp_code)
	stats[code] = 0

for rtype in my_req_type:														# Initialize stats dictionary to 0 based on user wanted request type (my_req_type)
	stats [rtype] = 0

# Set initialization

ip_list = set()																	# Contains list of Client's IPs	

#####

##### MAIN FUNCTION #####

logtail_that_file()

log = apachelogs.ApacheLogFile(logtail_file)											# Open "logtailed" file

for log_line in log:																	# Parse logfile line by line

	stats["nr_req"] += 1																# Increment total number of request
	ip_list.add(log_line.ip)															# Add IP to ip_list

	count_response_code(log_line.http_response_code)									# Count http response codes
	count_request_type(log_line.request_line)


# Remove localhost  from list of client's IPs
ip_list.discard("127.0.0.1")

# Count number of unique client's IPs
stats["ip_count"] = len(ip_list)


FNULL = open(os.devnull, 'w')

# Parse stats dictionary and sends result to zabbix
for metric in stats:
	zabbix_send(metric, stats[metric])


FNULL.close()

# os.remove(logtail_file)

