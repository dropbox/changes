define(['angular'], function(angular) {
  'use strict';

  angular.module('stream', [])
    .factory('Stream', function($window, $log){
      if ($window.streams === undefined) {
        $window.streams = {};
      }

      return function($scope, url, callback) {
        if ($window.streams[url]) {
          $log.info('[Stream] Closing connection to ' + url);
          window.streams[url].close();
        }
        $log.info('[Stream] Initiating connection to ' + url);

        $window.streams[url] = new EventSource(url + '?_=' + new Date().getTime());
        $window.streams[url].onopen = function(e) {
          $log.info('[Stream] Connection opened to ' + url);
        };

        $scope.$on("$destroy", function() {
          if (!$window.streams[url]) {
            return;
          }
          $log.info('[Stream] Closing connection to ' + url);
          $window.streams[url].close();
          delete window.streams[url];
        });

        return {
          subscribe: function(event, callback){
            $window.streams[url].addEventListener(event, function(e) {
              var data = $.parseJSON(e.data);
              $log.info('[Stream] Got event for ' + event);
              callback(data);
            }, false);
          }
        };
      };
    });
});
