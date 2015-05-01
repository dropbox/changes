define(['angular'], function(angular) {
  'use strict';

  angular.module('flash', [])
    .factory('flash', ['$rootScope', '$timeout', function($rootScope, $timeout){
      var messages = [],
          dismissible = true,
          reset,
          default_message = 'something happened, but we are not sure what';

      var cleanup = function() {
        $timeout.cancel(reset);
        reset = $timeout(function() {
          messages = [];
        });
      };

      var emit = function() {
        $rootScope.$emit('flash:message', messages, dismissible, cleanup);
      };

      $rootScope.$on('$routeChangeSuccess', emit);

      var getLevelTypeName = function(level) {
        if (level == 'error') {
          return 'danger';
        } else {
          return level;
        }
      };

      var asMessage = function(level, text) {
        if (text === undefined) {
          text = level;
          level = 'success';
        }
        return {
          type: getLevelTypeName(level),
          text: text || default_message
        };
      };

      var asArrayOfMessages = function(level, text) {
        if (level instanceof Array) return level.map(function(message) {
          return message.text ? message : asMessage(message);
        });
        return [asMessage(level, text)];
      };

      return function(level, text, isDismissible) {
        messages = asArrayOfMessages(level, text);
        if (isDismissible === false) {
          dismissible = false;
        }
        emit();
      };
    }])
    .controller('FlashCtrl', function($scope, $rootScope) {
        $scope.close = function(index) {
          $scope.messages.splice(index, 1);
        };

        $rootScope.$on('flash:message', function(_, messages, dismissible, done) {
          $scope.messages = messages;
          $scope.dismissible = dismissible;
          done();
        });

        $rootScope.$on('$stateChangeSuccess', function(_u1, _u2, $stateParams) {
          $scope.messages = [];
        });
    })
    .directive('flashMessages', function() {
      return {
        restrict: 'E',
        replace: true,
        template:
          '<ol class="alert-list" id="flash-messages">' +
            '<li ng-repeat="m in messages" class="alert alert-{{m.type}} alert-dismissable">' +
              '<div class="container">' +
                '<button ng-show=dismissible type="button" class="close" ng-click=close($index)>&times;</button>' +
                '<div ng-bind-html="m.text"></div>' +
              '</div>' +
            '</li>' +
          '</ol>',
        controller: 'FlashCtrl'
      };
    });
});
