define(['app', 'directives/flashMessages'], function(app) {
  app.controller('layoutCtrl', ['$scope', '$location', function($scope, $location) {
    'use strict';

    $scope.navClass = function(path) {
        return $location.path() == path ? 'active' : '';
    };

  }]);
});
