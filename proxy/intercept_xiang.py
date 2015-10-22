import sys, traceback, re
sys.path.append(".")
sys.path.append("/usr/local/lib/python2.7/site-packages")

from hashlib import sha1
from bs4 import BeautifulSoup
from bs4 import UnicodeDammit
from libmproxy.protocol.http import decoded
from time import time
import utilities
from urlparse import urlparse


def start(context, argv):
    if len(argv) < 2:
        raise ValueError('Usage: -s "intercept.py domain" -R http://host.com')
    context.domain = utilities.getEffectiveDomainFromURL(argv[1].lower().strip())
    if context.domain == None:
        raise ValueError('domain error Usage: -s "intercept.py domain" -R http://host.com')
    context.f = open('./log','w')

def request(context, flow):
    try:
        #if not context.domain in host:
        #    context.f.write('reject url: '+flow.request.url+'\n')
        #    return
        context.f.write('\nreceive request: %s\n'%flow.request.url)
        
        # set referer header if necessary
        complext_url_pattern = 'http:.+:8080/(http.+)'
        referer = None
        if flow.request.headers["Referer"] and len(flow.request.headers["Referer"]) >= 1:
            referer = flow.request.headers["Referer"][0].strip().lower();
            rs = re.match(complext_url_pattern, referer)
            if rs != None:
                flow.request.headers["Referer"] = [rs.group(1)]
                context.f.write('change referer header: '+rs.group(1)+'\n')
            else:
                context.f.write('not chaning referer: %s\n' %referer )
        #flow.request.headers["Referer"] = []
        #flow.request.headers["Cookie"] = []
        context.f.write('referer: %s %s\n' \
            %(str(type(flow.request.headers["Referer"])), str(flow.request.headers["Referer"]) ) )
        
        #set URL and host
        path = flow.request.path
        if path.startswith('/'):
            path = path[1:].lower().strip()
        if not path.startswith('http'):
            context.f.write('unmodified url: '+flow.request.url+'\n')
            o = urlparse(flow.request.url)
            flow.request.headers["Host"] = [o.netloc]
            return
        context.f.write('real_dest:'+path+'\n')
        o = urlparse(path)

        flow.request.url = path
        flow.request.host = o.netloc
        flow.request.headers["Host"] = [o.netloc]
        
        #set port if necessary
        if o.port:
            flow.request.port = o.port
        q = flow.request.get_query()
        context.f.write('query: \n' + str(q))
        context.f.write('host header: '+ str(flow.request.headers["Host"])+\
            ' new_url:'+flow.request.url+'\n' )
        #note query might need to set
    except Exception as e:
        context.f.write('error @request '+str(e))

def response(context, flow):
    try:
        url = flow.request.url
        if flow.request.host:
            host = flow.request.host
        else:
            host = ""
        context.f.write('\nreceive response: %s host:%s\n'%(flow.request.url, host) )
        with decoded(flow.response):  # Automatically decode gzipped responses.
            if (not "Content-Type" in flow.response.headers) or \
                len(flow.response.headers) == 0:
                return
            tp = flow.response.headers["Content-Type"][0].lower()
            context.f.write('  type:%s\n' %tp)
            if url.endswith('json'):
                return
            if "text/html" in tp:
                try:
                    soup = BeautifulSoup( flow.response.content, "html5lib")
                except Exception as e:
                    soup = BeautifulSoup( flow.response.content, 'lxml')
                
                if soup != None:
                    tags = soup.find_all()
                    for tag in tags:
                        if 'src' in tag.attrs:
                            context.f.write("src: %s\n" %tag['src'])
                        elif 'SRC' in tag.attrs:
                            context.f.write("src: %s\n" %tag['SRC'])
                            
                try:
                    flow.response.content = soup.prettify().encode('utf-8')
                    context.f.write('successfully store new content\n')
                except Exception as e:
                    context.f.write("error @response failed store new content exception: %s\n" \
                        %(str(e)))
                
                #analyzer.soup.head.insert(1, client_lib_node)
                #analyzer.soup.head.insert(1, esprima_node)
              
                #try:
                    #flow.response.content = analyzer.soup.prettify().encode('utf-8')
                    #context.f.write('newcontent:%s\n' %flow.response.content)
                #except Exception as e:
                    #context.f.write("  encoding exception: %s\n" %(str(e)))
                #t3 = time()
                #t = (t3 - t2) * 1000
                #context.f.write("REWRITE_TIME: %f ms\n" %(t))
                #context.f.write("  new HTML:\n %s  \n" %(flow.response.content) )
            #else:
                #pass
                #context.f.write('NOT rewriting %s %s response\n' % (flow.request.url,\
                #    flow.response.headers["Content-Type"]) )
            context.f.write('\n')
            
    except Exception as e:
        context.f.write('exception at %s for error: %s\n' %(url, str(e)))
        traceback.print_exc(file=context.f)

