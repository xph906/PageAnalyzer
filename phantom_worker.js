var queue = require('./Queue'),
  system = require('system'),
  taskWorker,
  /* parameters */
  address, times, index,
  /* settings */
  defaultUserAgent, userAgent, defaultTimeout, timeout,
  /* utilities */
  waitForTaskFinish, displayObject;
/*
var htmlparser = require("htmlparser2");
var parser = new htmlparser.Parser({
  onopentag: function(name, attribs){
      if(attribs.src && !attribs.async){
          console.log("JS! Hooray!");
      }
  },
  ontext: function(text){
      console.log("-->", text);
  },
  onclosetag: function(tagname){
      if(tagname === "script"){
          console.log("That's it?!");
      }
  }
}, {decodeEntities: true});
*/

/* Settings */
defaultUserAgent = 
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:38.0) Gecko/20100101 Firefox/38.0";
defaultAndroidUserAgent = 
  "Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30";
defaultTimeout = 5000;

function b64EncodeUnicode(str) {
    return btoa(encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, function(match, p1) {
        return String.fromCharCode('0x' + p1);
    }));
}

/* Task Worker */
taskWorker = (function (){
  var user_agent, timeout, current_url,
    task_queue = new queue(), page = null,
    fin_task_count = 0, err_task_count = 0,
    starting_time = 0, DOMContentLoaded_time = 0,
    error_tag = false,
    configure, post_task, start_tasks, 
    open_url, open_url_callback,
    get_remaining_task_count, get_fin_task_count, get_error_tag;

  configure = function(settings) {
    user_agent = settings.user_agent;
    timeout = settings.timeout;
  };

  post_task = function (task) {
    task_queue.enqueue(task);
    console.log("[ADD_TASK] adding a browsing task: " + 
      task_queue.getLength());
  };

  open_url_callback = function (result) {
    try{
      if (result.status !== 'success') {
        console.log('[FAIL] to load the address:'+result.url);
      }
      else {
        console.log("[SUCCEED] to load the address: " + result.url +
        ", contnet-size: "+result.content.length,
        ", failed objects: "+ result.failed_obj_count,
        ", landing-page: "+result.landing_page);
        //console.log(result.content);
        //send_contents(current_url, result.content, result.landing_page)
      }
    }
    catch (err) {
      console.log("[PHANTOM_ERR] error in open_url_callback "+err);
    }
    finally { 
      fin_task_count++;   
      if (task_queue.getLength() > 0) {
        //make sure the page is null!
        console.log("[INFO] Start next task, "+task_queue.getLength()+" left");
        start_tasks();
      }
    }
  };
  
  var createHAR = function (address, title, startTime, resources)
  {
    var entries = [];
    resources.forEach(function (resource) {
      var request = resource.request,
          startReply = resource.startReply,
          endReply = resource.endReply;

      if (!request || !startReply || !endReply) {
        return;
      }

      // Exclude Data URI from HAR file because
      // they aren't included in specification
      if (request.url.match(/(^data:image\/.*)/i)) {
        return;
      }

      entries.push({
        startedDateTime: request.time.toISOString(),
        time: endReply.time - request.time,
        request: {
            method: request.method,
            url: request.url,
            httpVersion: "HTTP/1.1",
            cookies: [],
            headers: request.headers,
            queryString: [],
            headersSize: -1,
            bodySize: -1
        },
        response: {
            status: endReply.status,
            statusText: endReply.statusText,
            httpVersion: "HTTP/1.1",
            cookies: [],
            headers: endReply.headers,
            redirectURL: "",
            headersSize: -1,
            bodySize: startReply.bodySize,
            content: {
                size: startReply.bodySize,
                mimeType: endReply.contentType
            }
        },
        cache: {},
        timings: {
            blocked: 0,
            dns: -1,
            connect: -1,
            send: 0,
            wait: startReply.time - request.time,
            receive: endReply.time - startReply.time,
            ssl: -1
        },
        pageref: address
      });
    });

    return {
      log: {
        version: '1.2',
        creator: {
            name: "PhantomJS",
            version: phantom.version.major + '.' + phantom.version.minor +
                '.' + phantom.version.patch
        },
        pages: [{
            startedDateTime: startTime.toISOString(),
            id: address,
            title: title,
            pageTimings: {
                onLoad: page.endTime - page.startTime
            }
        }],
        entries: entries
      }
    };
  };

  send_contents = function (url, contents, landing_url) {
    var db_listener = "http://localhost:4040/api/web-contents/contents-store",
      sender, error = null, 
      json_header, encoded_contents, data;
    sender = require('webpage').create();
    sender.settings.resourceTimeout = 5000;
    sender.settings.userAgent = user_agent; 

    sender.onResourceTimeout = function (e) {
      error = "timeout";
    };

    console.log("[INFO] sending contents to DB: "+contents.length);
    encoded_contents = b64EncodeUnicode(contents);
    data = '{"url":"' + encodeURIComponent(url) +
          '","landing_url":"' + encodeURIComponent(landing_url) +
          '","contents":"'+encoded_contents+'"}';
    console.log("[DEBUG] "+encoded_contents.length);
    json_header = { "Content-Type": "application/json" };
    try{
      sender.open(db_listener, 'post', data, json_header,
       function (status) {
        //page.render('github.png');
      
        sender.close();
        sender = null;
        
        if (status !== 'success'){
          err_task_count++;
          console.log("[FAIL] failed to send contents to DB; failed cases "+err_task_count);
        }
        else if (error) {
          err_task_count++;
          console.log("[FAIL] failed to send contents to DB; failed cases "+err_task_count);
        }
        console.log("[SUCCEED] sent contents ["+data.length+"] to db");
        //
      });
    }
    catch (err) {
      console.log("[PHANTOM_ERR] error sending contents to db "+err);
      sender.close();
      page = null;
      error_tag = true;
    }
    finally {
      fin_task_count++;
    } 
  };

  //this method creates and closes the page instance
  open_url = function (url) {
    var landing_page = url, content, timeout_count = 0,
      starting_time = 0, DOMContentLoaded_time = 0, tmp_time = 0,
      request_count = 0, response_count = 0;
    if (page !== null) {
      console.log("[ERROR] last instance hasn't finished!!!");
      return ;
    }
    starting_time = Date.now();
    page = require('webpage').create();
    page.settings.resourceTimeout = 5000;
    page.settings.userAgent = user_agent;
    
    page.onConsoleMessage = function (msg) { console.log(msg); };
    
    page.onCallback = function(data) {
        //Do whatever here
        var diff = (data - page.startTime)/1000;
        console.log('Main page is loaded and ready '+diff);
    };  
  
    page.onInitialized = function() {
      /** monitor ONDOMContentLoaded functions **/
      page.injectJs('hook.js');
    };
    /****************************/
    
    page.onLoadStarted = function () {
        page.startTime = new Date();
    };

    page.onResourceRequested = function (req) {
      //tmp_time = (Date.now() - starting_time)/1000;
      //console.log("[TIME] "+tmp_time+"s REQ:"+req.url);
      request_count++;
    };

    page.onResourceReceived = function (res) {
      if (res.stage !== "end") {
        return ;
      }
      tmp_time = (Date.now() - starting_time)/1000;
      //console.log("[TIME] "+tmp_time+"s RES:"+res.url+" "+JSON.stringify(res));
      response_count++;
    };

    page.onResourceTimeout = function (e) {
      timeout_count++;
    };

    console.log("[INFO] start browsing: "+url);
    try{
      var har = null;
      console.log("[INFO] start browsing: "+url);
      page.open(url, function (status) {
        //page.render('github.png');
        console.log("[INFO] done opening: "+url+" "+status);
        content = page.content.slice(0);
        if (status === "success"){
          //console.log("PAGE:"+page);
          landing_page = page.url.slice(0);
          
        }  
        har = createHAR(page.address, page.title, page.startTime, page.resources);  
        console.log("HAR INFO:"+JSON.stringify(har, undefined, 2));
        page.close();
        page = null;
        
        open_url_callback({
          status : status,
          url : url,
          landing_page : landing_page,
          request_count : request_count,
          response_count : response_count,
          failed_obj_count : timeout_count,
          content : content
        });
      });
    }
    catch (err) {
      console.log("[PHANTOM_ERR] error in open "+url+" error:"+err);
      page.close();
      page = null;
      error_tag = true;
    }
    finally { } 
  };

  start_tasks = function () {
    var task;
    if (task_queue.getLength()>0 && page === null) {
        task = task_queue.dequeue();
        current_url = task.url;
        open_url(task.url);
    }
    else {
      console.log("[INFO] can NOT start task: "+
        task_queue.getLength()+" "+page);
    }
  };

  get_remaining_task_count = function () {
    return task_queue.getLength();
  };

  get_fin_task_count = function() {
    return fin_task_count;
  };

  get_error_tag = function () {
    return error_tag;
  }

  return {
    configure : configure,
    post_task : post_task,
    start_tasks : start_tasks,
    get_remaining_task_count : get_remaining_task_count,
    get_fin_task_count : get_fin_task_count,
    get_error_tag : get_error_tag
  };

})();

/* Utilities */
displayObject = function (obj) {
  var item;
  for (item in obj) {
    if (obj.hasOwnProperty(item)) {
        console.log("KEY: "+ item+" VAL:"+obj[item]);
    }
  }
};

waitForTaskFinish = function(count) {
  if (!taskWorker.get_error_tag() &&
    taskWorker.get_fin_task_count() < count) {
    console.log("[MAIN] finished ["+taskWorker.get_fin_task_count() +
      "/"+count+"] tasks, check 20s later");
    setTimeout(function(){waitForTaskFinish(count)},
      20000);
  }
  else {
    console.log("[MAIN] having finished "+
      taskWorker.get_fin_task_count()+" tasks");
    phantom.exit();
  }
};

/* main */
if (system.args.length < 3) {
  console.log(
    "usage: phantom-worker.js url times timeout-for-one-req userAgent");
}
else {
  address = system.args[1];
  times = parseInt(system.args[2]);
  if (system.args.length >3 ){
    timeout = parseInt(system.args[3]);
  }
  else {
    timeout = defaultTimeout;
  }
  if (system.args.length > 4){
    userAgent = system.args[4];
  }
  else {
    userAgent = defaultAndroidUserAgent;
  }
  console.log("[MAIN] browsing "+address+" for "+times);
  taskWorker.configure({
    timeout : timeout,
    user_agent : userAgent });
  index = 0;
  while (index++ < times) {
    taskWorker.post_task({url : address});
  }
  taskWorker.start_tasks();
  waitForTaskFinish(times);
}


