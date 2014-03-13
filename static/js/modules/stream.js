define(['angular'], function(angular) {
  'use strict';

  angular.module('stream', [])
    .factory('stream', function($log){
      // TODO: channels should be API urls, which would let us simplify the logic
      // on the backend
      var Stream = function(url) {
        var self = this;

        this.url = url;
        this.es = null;

        this.channels = {
          // channelName: [scopeA, scopeB]
        };
        this.subscribers = {
          // eventName: [(scopeA, callbackA), (scopeB, callbackB)]
        };

        var arrPop = function(arr, el) {
          var idx = arr.indexOf(el);
          if (idx !== 1) {
            return arr.splice(idx, 1);
          }
          return;
        };

        return {
          addScopedSubscriber: function($scope, event, callback){
            // TODO: we should only parse the JSON once
            var listener = function(e) {
              var data = $.parseJSON(e.data);
              // $log.debug('[Stream] Got event for ' + event);
              callback(data);
            };

            if (self.subscribers[event] === undefined) {
              self.subscribers[event] = [[$scope, listener]];
            } else {
              self.subscribers[event].push([$scope, listener]);
            }

            $scope.$on('$destroy', function(){
              arrPop(self.subscribers[event], [$scope, listener]);
              if (self.subscribers[event].length === 0) {
                delete self.subscribers[event];
              }

              if (self.es) {
                self.es.removeEventListener(event, listener, false);
              }
            });

            if (self.es) {
              self.es.addEventListener(event, listener, false);
            }
          },
          addScopedChannels: function($scope, channels) {
            var reconnect = this.reconnect;
            var changed = false;

            $.each(channels, function(_, channel){
              if (self.channels[channel] === undefined) {
                self.channels[channel] = [$scope];
                changed = true;
              } else {
                self.channels[channel].push($scope);
              }
            });

            $scope.$on('$destroy', function(){
              var changed = false;

              $.each(channels, function(_, channel){
                arrPop(self.channels[channel], $scope);
                if (self.channels[channel].length === 0) {
                  arrPop(self.channels, channel);
                  changed = true;
                }
              });

              if (!changed) {
                return;
              }

              reconnect();
            });

            if (changed) {
              reconnect();
            }
          },
          reconnect: function() {
            if (self.es) {
              $log.info('[Stream] Closing connection to ' + self.url);
              self.es.close();
            }
            $log.info('[Stream] Initiating connection to ' + self.url);

            var querystring = '?_=' + new Date().getTime();
            $.each(self.channels, function(channel, _){
              querystring += '&c=' + encodeURIComponent(channel);
            });

            self.es = new EventSource(url + querystring);
            self.es.onopen = function(e) {
              $log.info('[Stream] Connection opened to ' + self.url);
            };

            $.each(self.subscribers, function(event, item){
              self.es.addEventListener(event, item[1], false);
            });
          }
        };
      };

      return new Stream('/api/0/stream/');
    });
});
