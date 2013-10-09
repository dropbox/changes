define(['app'], function(app) {
  app.controller('layoutCtrl', ['$scope', '$location', function($scope, $location) {
    'use strict';

    $scope.navClass = function(path) {
        return $location.path() == path ? 'active' : '';
    };

  }]);
});
