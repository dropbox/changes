define(['angular', 'jquery'], function(angular, $) {
  'use strict';

  angular.module('changes.poller', [])
    .factory('ItemPoller', function($http, $timeout){
      var default_options = {
        delay: 3000,
        errorDelay: 10000
      };

      return function ItemPoller(opts) {
        var options = {};
        $.extend(options, default_options);
        $.extend(options, opts);

        var endpoint = options.endpoint;
        var $scope = options.$scope;
        var pollTimeoutID;
        var stopped = (options.active === false);

        $scope.$on('$destroy', function(){
          if (pollTimeoutID) {
            $timeout.cancel(pollTimeoutID);
          }
        });

        var tick = function() {
          if (stopped) {
            pollTimeoutID = $timeout(tick, options.delay);
            return;
          }

          $http.get(options.endpoint, {
            ignoreLoadingBar: true
          }).success(function(response){
            $scope.$apply(function(){
              options.update(response);
            });
            pollTimeoutID = $timeout(tick, options.delay);
          }).error(function(){
            pollTimeoutID = $timeout(tick, options.errorDelay);
          });
        };

        tick();

        return {
          stop: function() {
            stopped = true;
          },
          start: function() {
            stopped = false;
          }
        };
      };
    })
    .factory('CollectionPoller', function(ItemPoller){
      var default_options = {
        transform: function(response) {
          return response;
        },
        shouldUpdate: function(item, existing) {
          return true;
        }
      };

      return function CollectionPoller(opts) {
        var options = {};
        $.extend(options, default_options);
        $.extend(options, opts);
        options.update = function(response) {
          response = options.transform(response);
          $.each(response, function(_ ,item){
            var existing = collection.indexOf(item);
            if (existing === -1) {
              return collection.unshift(item);
            }

            existing = collection[existing];
            if (options.shouldUpdate(item, existing)) {
              collection.update(item);
            }
          });
        };

        var collection = options.collection;
        return new ItemPoller(options);
      };
    });
});
