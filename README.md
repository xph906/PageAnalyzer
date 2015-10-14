# PageAnalyzer

# Steps to run:
1. Create log directory if necessary:
  mkdir logs

2. Start task server:
  python phantom_manager.py ./config

3. Start db_server if necessary: 
  node db_server.js

4. Post task to task server:
  python postTask.py ./config url times

# Note:
1. All configure information has been stored at `config` file. 
2. phantom_manager.py will send analysis results to mongodb through HTTP request:
  1. store results:
    POST http://db_server_host:db_server_port/api/webcontents/store/pageinfo
    Data: {
      "timestamp":processing_time,
      "url":the_url_of_the_page,
      "data": 
        { host : obj_size} }
  2. fetch results:
    POST http://db_server_host:db_server_port/api/webcontents/fetch/pageinfo
    Data: {
      "success":true|false, 
      "result":[
        { "timestamp":processing_time,
          "url":the_url_of_the_page, 
          "data": { 
            host : obj_size} }]
    }
3. db_server.js is hard-coded. When chaning db_related stuff in `config` file, please also change db_server.js.