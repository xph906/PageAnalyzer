import thread
import logging
import threading
import copy
import time
import os
import json
import pymongo
import subprocess
import urllib
import sys

logger = logging.getLogger('dbhandler')
hdlr = logging.FileHandler('./dbhandler.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.addHandler(consoleHandler)
logger.setLevel(logging.DEBUG)

class AdsProphetDBHandler:
	def __init__(self, config_obj):
		self.config = config_obj
		self.db_host = self.config['mongo_host']
		self.db_port = int(self.config['mongo_port'])
		self.db_name = self.config['db_name']
		self.conn = pymongo.MongoClient(	\
			self.db_host, self.db_port)
		if self.conn == None:
			logger.error("failed to connect to db "+self.db_name)
			return None

	def save_delay_info(self, info):
		try:
			logger.debug('debug @save_delay_info '+str(info) )
			db = getattr(self.conn, self.db_name)
			collection = db.delay_table
			collection.insert(info,check_keys=False)
		except Exception as e:
			logger.error('error @save_delay_info '+str(e))

	def fetch_delay_info(self, url):
		try:
			logger.debug('debug @fetch_delay_info '+url)
			db = getattr(self.conn, self.db_name)
			collection = db.delay_table
			results = collection.find({"url" : url})
			if results.count() == 0:
				return None
			else:
				delays = []
				for res in results:
					delays.append(res["delay"])
				len_delays = len(sorted(delays))
				delay = delays[len_delays/2]
			return delay	
		except Exception as e:
			logger.error('error @fetch_delay_info '+str(e))
			return None

	def fetch_hosts_info(self, url):
		try:
			logger.debug('debug @fetch_hosts_info '+url)
			db = getattr(self.conn, self.db_name)
			collection = db.pageinfo
			results = collection.find({"url":url})
			
			if results.count() == 0:
				return None
			else:
				hosts = []
				# check from the latest item
				results = sorted(results, \
					key=lambda x:int(x['timestamp']), reverse=True)
				for res in results:
					if res["data"] == "None":
						continue
					res_dict = eval(res["data"])
					if res_dict is None:
						continue
					for host in res_dict:
						host_dict = dict()
						host_dict["url"] = host
						hosts.append(host_dict)
					return hosts
				
				logger.info('@fetch_hosts_info: no hosts data: ' + \
					url + ' ' + str(len(results)))
				return None
			
		except Exception as e:
			logger.error('error @fetch_hosts_info '+str(e))
			return None

	#FIXME: modify this part to be consistent with previous methods 
	#  (i.e., no extra process)
	def post_task_to_manager(self, url,args):
		preargs = ['python']
		preargs[1:1] = [args["post_task_script_path"],args["self_path"],url,"5"]
        
		# start worker process 
		try:
			worker = subprocess.Popen(preargs)
			logger.debug('debug @post_task_to_manager done posting tasks '+url)
		except Exception as e:
			logger.error('error @post_task_to_manager '+str(e))
	
