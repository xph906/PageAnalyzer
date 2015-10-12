from multiprocessing import Process
import urlparse
import threading,argparse,subprocess,logging,Queue,os,time,sys
import psutil
import uuid
import psutil
import traceback
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from processPageObject import processPageInfo

logger = logging.getLogger('phantom')
hdlr = logging.FileHandler('./phantom.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.addHandler(consoleHandler)
logger.setLevel(logging.DEBUG)

def killProcess(pid):
    try:
        cmd = ['kill','-9','']
        cmd[2] = str(pid)
        subprocess.Popen(cmd)
    except Exception as e:
        logger.error("killProcess exception %s" % str(e))
        return

def killProcessAndChildProcesses(parent_pid):
    try:
        p = psutil.Process(parent_pid)
        child_pid = p.get_children(recursive=True)
        for pid in child_pid:
            killProcess(pid.pid)
        killProcess(parent_pid)
    except Exception as e:
        logger.error("killProcessAndChildProcesses exception %s" % str(e))
        return

# each Task object specifies the `url` to be browsed
# for `times` 
class Task:
    def __init__(self, url, time, callback):
        self.url = url
        self.times = time
        self.finished_times = 0
        self.callback = callback
        self.dirs = []
    def __str__(self):
        return "[%s for %d times]" %(self.url, self.times)

# A task is to browse a webpage for several times
# Manager's queue can queue many tasks
# but only one tast can run at a time
# A task needs multiple processes to run simultaneously
# The manager needs to check when a task is done and call callback method  
class Manager(threading.Thread):
    def __init__(self, task_queue, 
        timeout, user_agent, log_dir, 
        worker_script_path, remove_dirs=False):
        threading.Thread.__init__(self)
        self.__task_queue = task_queue
        self.__timeout = timeout
        self.__user_agent = user_agent
        self.__workers = []
        self.__log_dir = log_dir
        self.__remove_dirs = remove_dirs
        
        self.__worker_script_path = worker_script_path

        self.__total_worker_instances = 1

    def __launch_worker(self, task_data, index):
        url = task_data['url']
        token = str(uuid.uuid4())
        try:
            # prepare log path
            o = urlparse.urlparse(url)
            host = o.netloc
            dir_path_name = os.path.join(self.__log_dir, token)
            while os.path.exists(dir_path_name):
                token = str(uuid.uuid())
                dir_path_name = os.path.join(self.__log_dir, token)
            os.makedirs(dir_path_name)

            # prepar args
            args = ['phantomjs']
            args[1:1] = [self.__worker_script_path, url, str(self.__user_agent)]
            
            # start worker process 
            worker = subprocess.Popen(
                args, 
                stdout=open(os.path.join(dir_path_name,
                    'stdout.txt'), 'w'),
                stderr=open(os.path.join(dir_path_name,
                    'stderr.txt'), 'w'))
            worker_info = { 
                'timestamp' : int(time.time()),
                'index' : index,
                'process' : worker,
                'url' : url,
                'path' : dir_path_name }
                #(,task.url, index, worker, dir_path_name)
            #time.sleep(1)

            # update worker info
            self.__total_worker_instances += 1
            self.__workers.append(worker_info)
            logger.info("[MAIN] successfully run " +url+' : '+ 
                str(worker_info['index']) +
                " withpid:"+str(worker.pid)+
                ", dir_path:" + dir_path_name)
        except Exception as e:
            logger.error("failed to launch worker "+str(e))

    def run(self):
        current_task = None
        while True:
            try:
                # make sure current task has finished
                now = int(time.time())
                while len(self.__workers) > 0 and current_task:
                    #find the process that can be removed
                    index = 0
                    for worker in self.__workers:
                        starting_time = worker['timestamp']
                        proc = worker['process']
                        if now - starting_time > self.__timeout:
                            logger.info("[MAIN] worker[%d/%d] pid:%d url:%s timeout, kill it" 
                                % (worker['index'], current_task.times, proc.pid, worker['url']) )
                            killProcessAndChildProcesses(worker[3].pid)
                            break
                        else:
                            code = proc.poll()
                            if code != None:
                                logger.info("[MAIN] worker[%d/%d] pid:%d url:%s  exit(%s)" 
                                    % (worker['index'], current_task.times, proc.pid, 
                                        worker['url'], str(code)))
                                break
                            else:
                                #logger.info("[MAIN] worker[%d/%d] pid:%d url:%s is still running" 
                                #    % (worker['index'], current_task.times, proc.pid, worker['url']) )
                                pass
                        index += 1
                    
                    # remove the exited/killed process's info 
                    if index < len(self.__workers):
                        current_task.finished_times += 1
                        logger.info("[MAIN] remove worker with pid:%d. Done [%d/%d]" 
                            % ( proc.pid, current_task.finished_times, current_task.times) )
                        current_task.dirs.append(self.__workers[index]['path'])
                        del self.__workers[index] 
                    elif len(self.__workers) > 0:
                        time.sleep(1)

                # process results generated by current_task                
                if current_task:
                    current_task.callback({
                        'timestamp' : int(time.time()),
                        'path' : current_task.dirs,
                        'url' : current_task.url})
                    if self.__remove_dirs:
                        logger.info("[MAIN] remove dirs")
                        pass
                    current_task = None

                # start task if there is any
                # if not self.__task_queue.empty():
                try:
                    current_task = self.__task_queue.get(True)
                    logger.info("[MAIN] start task [%s]" %current_task  )
                    for i in range(current_task.times):
                        self.__launch_worker({'url':current_task.url}, i+1)
                except Queue.Empty as e:
                    #logger.debug("[MAIN] queue empty")
                    pass
                    
                #logger.info('[MAIN] no availble workers, try in 2s')
                #time.sleep(2)

            except Exception as e:
                traceback.print_exc()
                logger.error(
                    "failed to start task, repeat in 2s: "+str(e))   
                time.sleep(2) 

class MyHTTPServer(HTTPServer):
    def serve_forever(self, queue):
        self.RequestHandlerClass.task_queue = queue 
        HTTPServer.serve_forever(self)

class KodeFunHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header('Content-type','text-html')
            self.end_headers()
            
            o = urlparse.urlparse(self.path)
            task = urlparse.parse_qs(o.query)
            logger.info("receive path: "+self.path);
            logger.info("receive task:" + str(task) )
            url = task['url'][0]
            times = int(task['times'][0])
            
            self.wfile.write("task received: visit %s for %d times\n" 
                %(url, times) );
            #for i in range(times):
            self.task_queue.put(Task(url, times, taskDoneHandler))
            return
        except Exception as e:
            self.send_error(400, 'error'+str(e))

def extractBrowsingLogFromFolder(path_arr):
    results = []
    for path in path_arr:
        fname = os.path.join(path,'stdout.txt')
        if not os.path.exists(fname):
            logger.debug("[DEBUG] no stdout file in "+path)
            continue
        obj = {}
        for line in open(fname):
            if line.startswith('[ITEM]'):
                elems = line.split()
                host = elems[1].strip()
                size = int(elems[3])
                obj[host] = {'size' : size}
        logger.debug("[DEBUG] host size:"+str(len(obj)) )
        results.append(obj)
    return results

def taskDoneHandler(data):
    print "In testCallback %d" %data['timestamp']
    results = extractBrowsingLogFromFolder(data['path'])
    processPageInfo(data['url'], results)

def main():
    queue = Queue.Queue()
    #queue.put(Task("http://www.google.com",1))
    queue.put(Task("http://www.sina.com.cn",5,taskDoneHandler))
    #queue.put(Task("http://www.qq.com",10))
    #queue.put(Task("http://www.weibo.com",10))
    #queue.put(Task("http://www.wsj.com",10))
    #queue.put(Task("http://www.baidu.com",10))
    #queue.put(Task("https://en.wikipedia.org/wiki/Main_Page",10))
    #queue.put(Task("http://www.yahoo.com",10))
    defaultUserAgent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:38.0) Gecko/20100101 Firefox/38.0"
    defaultAndroidUserAgent = "Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30";


    if len(sys.argv) != 3:
        print "usage: python phantom_manager.py log_dir phanton_worker.js_path"
        return
    log_dir = sys.argv[1]
    worker_script_path = sys.argv[2]
    #task_queue, worker_count,
    #    timeout, user_agent, log_dir, worker_script_path
    #manager = Manager(queue, 10, 120, defaultAndroidUserAgent,log_dir,worker_script_path)
    #task_queue, timeout, user_agent, log_dir, 
    #    worker_script_path
    manager = Manager(queue, 120, defaultAndroidUserAgent, log_dir, worker_script_path)
    manager.start()
    time.sleep(2)
    #queue.join()
    server_address = ('127.0.0.1', 8082)
    
    httpd = MyHTTPServer(server_address, KodeFunHTTPRequestHandler)
    logger.info('http server is running...')
    try:
        httpd.serve_forever(queue)
    except KeyboardInterrupt:
        pass
    httpd.server_close()

if __name__ == "__main__":
    main()


