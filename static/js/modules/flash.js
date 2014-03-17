define(['angular'], function(angular) {
  'use strict';

  angular.module('flash', [])
    .factory('flash', ['$rootScope', '$timeout', function($rootScope, $timeout){
      var messages = [],
          reset;

      var cleanup = function() {
        $timeout.cancel(reset);
        reset = $timeout(function() {
          messages = [];
        });
      };

      var emit = function() {
        $rootScope.$emit('flash:message', messages, cleanup);
      };

      $rootScope.$on('$routeChangeSuccess', emit);

      var asMessage = function(level, text) {
        if (!text) {
          text = level;
          level = 'success';
        }
        return {
          level: level,
          text: text
        };
      };

      var asArrayOfMessages = function(level, text) {
        if (level instanceof Array) return level.map(function(message) {
          return message.text ? message : asMessage(message);
        });
        return text ? [{ level: level, text: text }] : [asMessage(level)];
      };

      return function(level, text) {
        emit(messages = asArrayOfMessages(level, text));
      };
    }])
    .directive('flashMessages', function() {
      return {
        restrict: 'E',
        replace: true,
        template:
          '<ol class="alert-list" id="flash-messages">' +
            '<li ng-repeat="m in messages" class="alert alert-{{levelClassName(m.level)}} alert-dismissable">' +
              '<div class="container">' +
                '<button type="button" class="close" data-dismiss="alert">&times;</button>' +
                '{{m.text}}' +
              '</div>' +
            '</li>' +
          '</ol>',
        controller: function($scope, $rootScope) {
          $scope.levelClassName = function(level) {
            if (level == 'error') {
              return 'danger';
            } else {
              return level;
            }
          };

          $rootScope.$on('flash:message', function(_, messages, done) {
            $scope.messages = messages;
            done();
          });

          $rootScope.$on('$stateChangeSuccess', function(_u1, _u2, $stateParams){
            $scope.messages = [];
          });
        }
      };
    });
});
