import json
import urllib2
import urllib
import sys
import base64
import os
import urlparse
import logging
import math
import traceback
import tldextract

logger = logging.getLogger('Utility')
hdlr = logging.FileHandler('./utilities.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.addHandler(consoleHandler)
logger.setLevel(logging.DEBUG)

def getEffectiveDomainFromURL(url):
  try:
    url = url.lower().strip()
    if not url.startswith('http'):
      url = 'http://'+url
    no_fetch_extract = tldextract.TLDExtract(suffix_list_url=False)
    o = no_fetch_extract(url.lower())
    return o.domain + '.' + o.suffix
  except Exception as e:
    logger.error( "error in getting getEffectiveDomain "+str(e))
    return None


def main():
  print getEffectiveDomainFromURL(sys.argv[1])

if __name__=="__main__":
    main()
