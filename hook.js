try {
  var reg_time = Date.now();
  //console.log("[DEBUG] HOOK");
  document.addEventListener('DOMContentLoaded', function() {
    var DOMContentLoaded_time = (Date.now() - reg_time) / 1000;
    window.callPhantom(Date.now());
    //console.log("[TIME] "+DOMContentLoaded_time+"s DOMContentLoaded");
  }, false);
}
catch (e) {
  //console.log("[ERROR] [REGISTER DOMContentLoaded] "+e);
}
