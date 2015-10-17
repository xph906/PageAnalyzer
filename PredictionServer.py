from twisted.internet.protocol import ServerFactory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor
import thread
import threading
import copy
import time
import os
import json
import pymongo
import subprocess
import urllib
import sys

from DBHandler import AdsProphetDBHandler

args = None

def readConfigure(path):
    data = json.load(open(path))
    data['self_path'] = path
    return data

'''
def save_delay_info(info):
	conn = pymongo.MongoClient("127.0.0.1",27017)
	db = conn.webdb
	collection = db.delay_table
	collection.insert(info,check_keys=False)

def fetch_delay_info(url):
	conn = pymongo.MongoClient("127.0.0.1",27017)
	db = conn.webdb
	collection = db.delay_table
	results = collection.find({"url":url})
	if results.count() == 0:
		return None
	else:
		delays = []
		for res in results:
			delays.append(res["delay"])
		len_delays = len(sorted(delays))
		delay = delays[len_delays/2]
		return delay	

def fetch_hosts_info(url):
	conn = pymongo.MongoClient("127.0.0.1",27017)
	db = conn.webdb
	collection = db.pageinfo
	results = collection.find({"url":url})
	if results.count() == 0:
		#post task
		return None
	else:
		hosts = []
		for res in results:
			if res["data"] == "None":
				return None
			res_dict = eval(res["data"])
			if res_dict is None:
				print 'no hosts data'
				return None
			for host in res_dict:
				host_dict = dict()
				host_dict["url"] = host
				hosts.append(host_dict)
			break
		#print hosts 
		return hosts	

def post_task_to_manager(url,args):
	print args["post_task_script_path"]
	preargs = ['python']
	preargs[1:1] = [args["post_task_script_path"],args["self_path"],url,"5"]
        
	# start worker process 
	try:
		worker = subprocess.Popen(preargs)
		print "[DONE] done posting task to manager: "+url
	except Exception as e:
		print "[ERROR] failed to post task to manager"
'''        

class DataProtocol(LineReceiver):

	def __init__(self):
		pass

	def connectionMade(self):
 		pass
	        #print '[Server]client connect'
	        #print self.transport.getPeer()

	def lineReceived(self,line):
		tag = line[0]
		if tag == '0':
			print '[Server]Prediction request recieved'
			data_src = line[1:]
			data_obj = json.loads(data_src)
			if type(data_obj) == dict:
				for (k,v) in data_obj.iteritems():
					print '%s:%s' % (k,v)					
			else:
				print '[Server]request format error'
				return
			#send response to client
			response_obj = dict()
			url = urllib.unquote(data_obj["url"])	
			
			# add prediction logic here
			# put prediction logic in a independent class, such as
			#    PredictionEngine.mode1, PredictionEngine.mode2 ...
			# the delay is an array
			delay = self.factory.db_handler.fetch_delay_info_from_url(url)
			if delay is not None:
				print '[Server]fetch delay info ',str(delay)
				if len(delay) > 20:
					delay = delay[:20]
				response_obj["delay"] = delay
			else:
				response_obj["delay"] = "None"
			hosts = self.factory.db_handler.fetch_hosts_info(url)
			if hosts is not None:
				print '[Server]fetch hosts info'
				if len(hosts) == 0:
					print '[Server]No hosts'
					response_obj["hosts"] = "None"
				else:
					print 'found hosts: '+str(hosts)
					response_obj["hosts"] = hosts
			else:
				response_obj["hosts"] = "None"
				#post task to page_analyzer
				self.factory.db_handler.post_task_to_manager(url,self.factory.args)
				
			str_response = str(response_obj)+"\r\n"
			self.transport.write(str_response)				
		elif tag == '1':
			print '[Server]User data history recieved'
			data_src = line[1:]
			data_obj = json.loads(data_src)
			url = urllib.unquote(data_obj["url"])
			data_obj["url"] = url

			if type(data_obj) == dict:
				self.factory.db_handler.save_delay_info(data_obj)
				for (k,v) in data_obj.iteritems():
					print '%s:%s' % (k,v)	
			else:
				print '[Server]requset format error'
		else:
			print '[Server]command format error'

	def connectionLost(self,reason):
        	#print '[Server]client connection finish'
		pass

class DataFactory(ServerFactory):

	protocol=DataProtocol

	def __init__(self,args,db_handler):
		self.args = args
		self.db_handler = db_handler
	

def main():
	if len(sys.argv) != 2:
	        print "usage: python PredictionServer.py config_file"
	        return
	args = readConfigure(sys.argv[1])
	print args
	db_handler = AdsProphetDBHandler(args)
	factory = DataFactory(args, db_handler)
	port = reactor.listenTCP(args["prediction_server_port"],factory)
	print 'Serving on %s.' % (port.getHost())
	reactor.run()	


if __name__== '__main__':
	main()
#	post_task_to_manager("http://www.baidu.com/")
#	fetch_delay_info("http://www.baidu.com/")
#	fetch_hosts_info("http://m.baidu.com/news?fr=mohome&ssid=0&from=844b&uid=&pu=sz@1320_1001,ta@iphone_2_4.4_3_537&bd_page_type=1")
#	test_info = 						{"url":"zjulist.test1.com","delay":1000,"signal":-60,"wifiname":"HIWIFI","location":"12/23/1","model":"MI","timestamp":"2015/10/11-12:16","rtts":[{"url":"zjulist1.com","rtt":12},{"url":"zjulist1.com","rtt":12}]}
#	save_delay_info(test_info);

