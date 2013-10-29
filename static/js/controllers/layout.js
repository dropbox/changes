define(['app'], function(app) {
  app.controller('layoutCtrl', ['$scope', '$location', '$http', function($scope, $location, $http) {
    'use strict';

    $scope.authenticated = null;
    $scope.user = null;
    $scope.navPath = null;

    $scope.$on('$routeChangeSuccess', function(){
      $scope.navPath = $location.path();
    });

    $http.get('/api/0/auth/')
      .success(function(data){
      	$scope.authenticated = data.authenticated;
      	$scope.user = data.user || {};
      });

    $('.navbar-auth').show();
  }]);
});
