var page = require('webpage').create();
var system = require('system');

page.onInitialized = function() {
    page.onCallback = function(data) {
        console.log('Main page is loaded and ready '+data);
        //Do whatever here
    };

    page.evaluate(function() {
        document.addEventListener('DOMContentLoaded', function() {
            window.callPhantom(Date.now());
        }, false);
        console.log("Added listener to wait for page ready");
    });

};

page.open('https://www.google.com', function(status) {});