from multiprocessing import Process
import urlparse
import threading,argparse,subprocess,logging,Queue,os,time,sys
import psutil
import uuid
import psutil
import traceback
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer


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
    def __init__(self, url, time):
        self.url = url
        self.times = time

class Manager(threading.Thread):
    def __init__(self, task_queue, worker_count,
        timeout, user_agent, log_dir, worker_script_path):
        threading.Thread.__init__(self)
        self.__task_queue = task_queue
        self.__worker_count = worker_count
        self.__timeout = timeout
        self.__user_agent = user_agent
        self.__workers = []
        self.__log_dir = log_dir
        self.__total_worker_instances = 1
        self.__worker_script_path = worker_script_path

    def __launch_worker(self, task):
        token = str(uuid.uuid4())
        try:
            # prepare log path
            o = urlparse.urlparse(task.url)
            host = o.netloc
            path_name = host + '_' + token
            full_path_name = os.path.join(self.__log_dir,path_name)
            if not os.path.exists(full_path_name):
                os.makedirs(full_path_name)
            
            # prepar args
            args = ['phantomjs']
            args[1:1] = [self.__worker_script_path, task.url, str(task.times)]
            
            # start worker process 
            worker = subprocess.Popen(
                args, 
                stdout=open(os.path.join(full_path_name,
                    'stdout.txt'), 'w'),
                stderr=open(os.path.join(full_path_name,
                    'stderr.txt'), 'w'))
            # [starting_time, url, times, popen-obj]
            worker_info = (int(time.time()),task.url, task.times, worker)
            time.sleep(1)

            # update worker info
            self.__total_worker_instances += 1
            self.__workers.append(worker_info)
            logger.info("[MAIN] successfully run " + worker_info[1] +
                " withpid:"+str(worker.pid)+
                ", full_path:" + full_path_name)
        except Exception as e:
            logger.error("failed to launch worker "+str(e))

    def run(self):
        while True:
            try:
                # check and kill dead process
                now = int(time.time())
                while len(self.__workers) > 0:
                    index = 0
                    for worker in self.__workers:
                        starting_time = worker[0]
                        proc = worker[3]
                        if now - starting_time > self.__timeout:
                            logger.info("[MAIN] TIMEOUT worker[%d] %s pid:%d" 
                                % (index, worker[1], worker[3].pid) )
                            killProcessAndChildProcesses(worker[3].pid)
                            break
                        else:
                            code = proc.poll()
                            if code != None:
                                logger.info("[MAIN] EXIT[%s] worker[%d] %s pid[%s]" 
                                    % (str(code), index, worker[1], str(worker[3].pid) ) )
                                #killProcess(worker[3].pid)
                                #killProcessAndChildProcesses(worker[3].pid)
                                break
                            else:
                                logger.info("[MAIN] process %d is still running" % worker[3].pid)
                        index += 1
                    if index >= len(self.__workers):
                        logger.info("[MAIN] all %d workers are in processing"
                            % len(self.__workers))
                        break
                    else:
                        logger.info("[MAIN] worker[%d] %s finished its job, kill it" 
                            % (index, self.__workers[index][1]) )
                        del self.__workers[index] 

                # start task if there is any
                #if not self.__task_queue.empty():
                while len(self.__workers) < self.__worker_count:
                    try:
                        if len(self.__workers) > 0:
                            task = self.__task_queue.get(True, 10)
                            logger.info("[MAIN] allocate task [%s] to a worker [%d instance running]" 
                                % (task.url, len(self.__workers)) )
                            self.__launch_worker(task)
                        else:
                            logger.info('[MAIN] no working process ... ')
                            task = self.__task_queue.get()
                            logger.info("[MAIN] allocate task [%s] to a worker [%d instance running]" 
                                % (task.url, len(self.__workers)) )
                            self.__launch_worker(task)
                    except Queue.Empty as e:
                        logger.debug("[MAIN] queue empty timeout")
                        break
                    

                #logger.info('[MAIN] no availble workers, try in 2s')
                time.sleep(5)

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
            
            self.wfile.write("task received: %s for %d times\r\n" 
                %(url, times) );

            self.task_queue.put(Task(url,times))
            return
        except Exception as e:
            self.send_error(400, 'error'+str(e))

def main():
    queue = Queue.Queue()
    queue.put(Task("http://www.google.com",1))
    #queue.put(Task("http://www.sina.com.cn",10))
    #queue.put(Task("http://www.qq.com",10))
    #queue.put(Task("http://www.weibo.com",10))
    #queue.put(Task("http://www.wsj.com",10))
    #queue.put(Task("http://www.baidu.com",10))
    #queue.put(Task("https://en.wikipedia.org/wiki/Main_Page",10))
    #queue.put(Task("http://www.yahoo.com",10))
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:38.0) Gecko/20100101 Firefox/38.0"
    if len(sys.argv) != 3:
        print "usage: python phantom_manager.py log_dir phanton_worker.js_path"
        return
    log_dir = sys.argv[1]
    worker_script_path = sys.argv[2]
#task_queue, worker_count,
    #    timeout, user_agent, log_dir, worker_script_path
    manager = Manager(queue, 10, 120, user_agent,log_dir,worker_script_path)
    manager.start()
    time.sleep(10)
    #queue.join()
    server_address = ('127.0.0.1', 8082)
    
    httpd = MyHTTPServer(server_address, KodeFunHTTPRequestHandler)
    logger.info('http server is running...')
    httpd.serve_forever(queue)


if __name__ == "__main__":
	main()


