(function(){
  'use strict';

  define(['app'], function(app) {
    app.controller('layoutCtrl', [
        '$scope', '$rootScope', '$location', '$http', '$document',
        function($scope, $rootScope, $location, $http, $document) {
      $scope.projectList = [];
      $scope.authenticated = null;
      $scope.user = null;
      $scope.navPath = null;

      $scope.$on('$routeChangeSuccess', function(){
        $scope.navPath = $location.path();
        $rootScope.pageTitle = 'Changes';
        $rootScope.activeProject = null;
      });

      $http.get('/api/0/auth/')
        .success(function(data){
          $scope.authenticated = data.authenticated;
          $scope.user = data.user || {};
        });

      $http.get('/api/0/projects/')
        .success(function(data){
          $scope.projectList = data;
        });

      $rootScope.$watch('pageTitle', function(value) {
        $document.title = value;
      });

      $('.navbar .container').show();
    }]);
  });
})();
