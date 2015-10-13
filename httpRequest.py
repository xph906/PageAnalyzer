import urllib2
import urllib
import sys
from bs4 import BeautifulSoup
from urlparse import urlparse

# req_obj.url
# req_obj.user_agent
# req_obj.method
# req_obj.timeout
# req_obj.post_params 
def requestPage(req_obj):
  opener = urllib2.build_opener()
  opener.addheaders = [('User-agent', req_obj['user_agent'])]
  urllib2.install_opener(opener)
  try:
    if req_obj['method'] == 'GET':
      f = urllib2.urlopen(req_obj['url'], timeout=req_obj['timeout'] )
      return f.read()
    elif req_obj['method'] == "POST":
      params = urllib.urlencode(req_obj['post_params'] )
      req = urllib2.Request(req_obj['url'], params) 
      response = urllib2.urlopen(req, timeout=req_obj['timeout'])
      return response.read()
    else:
      print "error method"
      return None
  except Exception as e:
    print "error ",e
    return None

def createDefaultReqObj(url, method, post_params={}):
  req_obj = {  \
    'url' : url, \
    'user_agent' : "Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30", \
    'method' : method.upper(), \
    'timeout' : 10, \
    'post_params' : post_params}
  return req_obj

def analyzePage(content, url):
  soup = BeautifulSoup(content, 'html5lib')
  obj_dict = {}
  obj_list = []
  count = 0
  for tag in soup.find_all(src=True):
    url = tag['src'].strip()
    if not url in obj_dict:
      obj_dict[url] = 1
    else:
      obj_dict[url] += 1
    count += 1
    obj_list.append(url)
  print "the number of objects: ", str(count)
  #for url in obj_dict:
  #  print url, str(obj_dict[url])
  for url in obj_list:
    print url

def main():
  req_obj = createDefaultReqObj(sys.argv[1], 'GET')
  #req_obj = createDefaultReqObj(sys.argv[1], 'POST')
  rs = requestPage(req_obj)
  if rs == None:
    return
  print "done getting %s, size %d" %(sys.argv[1], len(rs))
  analyzePage(rs, sys.argv[1])

if __name__ == "__main__":
  main()


  
  