define(['app', 'factories/flash'], function (app) {
  app.directive('flashMessages', function() {
    'use strict';
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
          switch (level) {
            case 'error':
              return 'danger';
            default:
              return level;
          }
        }
        $rootScope.$on('flash:message', function(_, messages, done) {
          $scope.messages = messages;
          done();
        });
      }
    };
  });
});
