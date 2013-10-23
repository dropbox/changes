define(['app'], function (app) {
  app.factory('stream', ['$window', function(window){
    'use strict';

    if (window.streams === undefined) {
      window.streams = {};
    }

    return function($scope, url, callback) {
      if (window.streams[url]) {
        console.log('[Stream] Closing connection to ' + url);
        window.streams[url].close()
      }
      console.log('[Stream] Initiating connection to ' + url);

      window.streams[url] = new EventSource(url + '?_=' + new Date().getTime());
      window.streams[url].onopen = function(e) {
        console.log('[Stream] Connection opened to ' + url);
      }

      $scope.$on("$destroy", function() {
        console.log('[Stream] Closing connection to ' + url);
        window.streams[url].close();
        delete window.streams[url];
      });

      return {
        subscribe: function(event, callback){
          window.streams[url].addEventListener(event, function(e) {
            var data = $.parseJSON(e.data);
            callback(data);
          }, false);
        }
      }
    };
  }]);
});
