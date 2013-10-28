define(['app', 'directives/flashMessages'], function(app) {
  app.controller('layoutCtrl', ['$scope', '$location', '$http', function($scope, $location, $http) {
    'use strict';

    $scope.authenticated = null;
    $scope.user = null;

    $('.navbar-auth').show();

    $http.get('/api/0/auth/')
      .success(function(data){
      	$scope.authenticated = data.authenticated;
      	$scope.user = data.user || {};
      });

    $scope.navClass = function(path) {
        return $location.path() == path ? 'active' : '';
    };

  }]);
});
