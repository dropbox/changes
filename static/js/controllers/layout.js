define(['app'], function(app) {
  app.controller('layoutCtrl', ['$scope', '$rootScope', '$location', '$http', function($scope, $rootScope, $location, $http) {
    'use strict';

    $scope.projectList = [];
    $scope.authenticated = null;
    $scope.user = null;
    $scope.navPath = null;

    $scope.$on('$routeChangeSuccess', function(){
      $scope.navPath = $location.path();
      $rootScope.activeProject = null;
    });

    $http.get('/api/0/auth/')
      .success(function(data){
      	$scope.authenticated = data.authenticated;
      	$scope.user = data.user || {};
      });

    $http.get('/api/0/projects/')
      .success(function(data){
        $scope.projectList = data.projects;
      });

    $('.navbar .container').show();
  }]);
});
