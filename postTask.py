import urllib2
import urllib
import sys
import json

def readConfigure(path):
    data = json.load(open(path))
    return data

def postTask(url, times, args):
	template = "http://" + args['task_server_host'] + ":" + str(args['task_server_port']) +\
		"/task?url=%s&times=%d"
	print template
	url_par = urllib.quote(url)
	times_par = int(times)
	url = template%(url_par,times_par)
	#print url
	response = urllib2.urlopen(url)
	response_contents = response.read()
	print response_contents
	print ""

def sendTaskFromFile(file_name):
	f = open(file_name)
	for line in f:
		url = line.strip()
		print "post task : url %s , times %d" %(url, 1)
		sendTask(url,1)


def main():
	if len(sys.argv) != 4:
		print "usage: python postTask.py config task_url task_times"
		return 
	args = readConfigure(sys.argv[1])
	postTask(sys.argv[2],sys.argv[3], args)

if __name__ == "__main__":
	main()
#sendTaskFromFile(sys.argv[1])
