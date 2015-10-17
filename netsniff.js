/* Const Value */
/* Settings */
defaultUserAgent = 
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:38.0) Gecko/20100101 Firefox/38.0";
defaultAndroidUserAgent = 
  "Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30";
defaultTimeout = 5000;

if (!Date.prototype.toISOString) {
    Date.prototype.toISOString = function () {
        function pad(n) { return n < 10 ? '0' + n : n; }
        function ms(n) { return n < 10 ? '00'+ n : n < 100 ? '0' + n : n }
        return this.getFullYear() + '-' +
            pad(this.getMonth() + 1) + '-' +
            pad(this.getDate()) + 'T' +
            pad(this.getHours()) + ':' +
            pad(this.getMinutes()) + ':' +
            pad(this.getSeconds()) + '.' +
            ms(this.getMilliseconds()) + 'Z';
    }
}

var page = require('webpage').create(),
    system = require('system');
var urlParser = require('url');



function createHAR(address, title, startTime, resources)
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
            fullTime: endReply.time - page.startTime,
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
                    onLoad: page.endTime - page.startTime,
                    onDOMContentLoaded : page.DOMContentLoadedTime - page.startTime
                }
            }],
            entries: entries
        }
    };
}
/*
 * return value:
 *   { host : { size : %d, number : %d}}
 */
function analyzeHAR(completeHarObject)
{
    try{
        var harObj = completeHarObject.log;
        var domContentLoadedTime = harObj.pages[0].pageTimings.onDOMContentLoaded;
        var pageURL = harObj.pages[0].id;
        
        var results = {};

        if (!domContentLoadedTime || domContentLoadedTime <= 0) {
            console.log("[ERROR] @analyzeHAR domContentLoadedTime is not valid");
            return null;
        }
        harObj.entries.forEach( function(elem){
            var url = elem.request.url;
            var time = elem.time;
            var full_time = elem.fullTime;
            var size = elem.response.content.size;
            var type = elem.response.content.mimeType;
            if (full_time > domContentLoadedTime) {
                return;
            }
        
            var urlComponents = urlParser.parse(url, true, true);
            var hostname = urlComponents.protocol + "//" + urlComponents.hostname;
            //console.log(hostname+" size:"+size+" type:"+type+" fulltime:"+full_time);
            if (hostname in results) {
                results[hostname].size += size;
                results[hostname].number += 1;
                results[hostname].latency += time
            }
            else {
                results[hostname] = {'size':size, 'number':1, 'latency':time};
            }
        });
        for (var item in results) {
            console.log('[ITEM] '+item+" => "+results[item].size+" "+
                results[item].number+" "+results[item].latency);
        }
        return results;
    }
    catch (e) {
        console.log('[ERROR] @analyzeHAR '+e);
        return null;
    }
    
}


if (system.args.length === 1) 
{
    console.log('Usage: netsniff.js <some URL>');
    phantom.exit(1);
} 
else 
{
	var userAgent = defaultAndroidUserAgent;
	var timeout = defaultTimeout;
    page.address = system.args[1];
    if (system.args.length === 3) {
    	userAgent = system.args[2];
    }
    if (system.args.length === 4) {
    	timeout = Number.parseInt(system.args[3]);
    }
    console.log("userAgent:"+userAgent+" timeout:"+timeout);
    page.resources = [];
    page.settings.resourceTimeout = timeout;
    page.settings.userAgent = userAgent;

    page.onCallback = function(data) {
        page.DOMContentLoadedTime = data;
    };  
  
    page.onInitialized = function() {
      /** monitor ONDOMContentLoaded functions **/
      page.injectJs('hook.js');
    };

    page.onLoadStarted = function () {
        page.startTime = new Date();
    };

    page.onResourceRequested = function (req) {
        page.resources[req.id] = {
            request: req,
            startReply: null,
            endReply: null
        };
    };

    page.onResourceReceived = function (res) {
        if (res.stage === 'start') {
            page.resources[res.id].startReply = res;
        }
        if (res.stage === 'end') {
            page.resources[res.id].endReply = res;
        }
    };

    page.open(page.address, function (status) {
        if (status !== 'success') {
            console.log('[ERROR] @page.open fail to load the address');
            phantom.exit(1);
        } else {
            page.endTime = new Date();
            //page.title = page.evaluate(function () {
            //    return document.title;
            //});
            
        }
        try {
            var har = createHAR(page.address, page.title, page.startTime, page.resources);
            
            analyzeHAR(har);
            //console.log(JSON.stringify(har, undefined, 4));
            phantom.exit(0);
        }
        catch (e) {
            console.log("[ERROR] @page.open " + e);
            phantom.exit(1);
        }
    });
}

//Timeout
setTimeout(
    function(){
        console.log("[TIMEOUT]");
        var har = createHAR(page.address, page.title, page.startTime, page.resources);
        analyzeHAR(har);
        phantom.exit(1);
    }, 10000);
