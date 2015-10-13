var express = require('express');
var querystring = require('querystring');
var urlParse = require('url');
var bodyParser = require('body-parser');
var util = require('util');

var mongo = require('mongodb');
var monk = require('monk');
var db = monk('localhost:27017/webdb');

var app = express();
app.use(bodyParser({limit: '50mb'}));
app.use(bodyParser.json() );


app.use(function(req,res,next){
    req.db = db;
    next();
});

var processURL = function(url){
  var new_url = querystring.unescape(url);
  var o = urlParse.parse(new_url)
  new_url = o.protocol+'//'+o.host+o.path;
  return new_url.toLowerCase()
}
/* Store Distance */
app.post('/api/webcontents/store/pageinfo', function (req, res) {
	if ( !req.body.timestamp || !req.body.url || !req.body.data ) {
		console.log(req.body.timestamp+" "+req.body.url+" "+req.body.data);
		return res.json({success : false, message : "incomplete body"});
	}
	try{
    var url = processURL(req.body.url);
	  res.json({
  		success : true,
  		url : url});
	}
	catch (e) {
		console.log("error: "+e);
		res.json({
  		success : false,
  		message : e});
	}
  
  try{
	  var collection = db.get('pageinfo');
	  collection.insert({
	  	url : url, data : req.body.data, timestamp : req.body.timestamp
	  }, function (err, doc) {
	    if (err) {
	        console.log("[FAIL] failed to insert page info into DB: "
	        	+err+" "+url);
	    }
	    else {
	        console.log("[SUCC] inserted page info into DB: "+url);
	    }} );
  
  }
  catch (e) {
  	console.log("[FAIL] failed to insert page info into DB "+e);
  }
});


/* Fetch distance */
app.post('/api/webcontents/fetch/pageinfo', function (req, res){
	var url, data, index, collection;
	if ( !req.body.url ) {
		res.json({success : false, message : "incomplete body"});
		return
	}
	try{
		if (req.body.url === "*" ) {
			data = {}
		}
		else {
  		var url = processURL(req.body.url);
  		data = {url : url}
		}
  	console.log("  [DEBUG] fetch pageinfo : " + data);
	  collection = db.get('pageinfo');
	  collection.find(data, function (err, docs) {
	    if (err) {
	        console.log("[FAIL] failed to fetch pageinfo for "+url);
	        res.json({
  					success : false
  				});
	    }
	    else {
	        console.log("[SUCC] succeeded to fetch pageinfo for " + docs.length +' items');
	   
	        res.json({
  					success : true,
  					result : JSON.stringify(docs)
  				});
	    }} );
  }
  catch (e) {
  	console.log("[FAIL] failed to process req "+e);
  	res.json({ success : false, message : e});
  }	
});

var server = app.listen(4040, function () {

  var host = server.address().address;
  var port = server.address().port;

});
