(function(){
  'use strict';

  define(['app', 'modules/notify', 'modules/flash'], function(app) {
    app.controller('layoutCtrl', [
        '$scope', '$rootScope', '$location', '$http', '$document', 'notify', 'flash',
        function($scope, $rootScope, $location, $http, $document, notify, flash) {
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

          notify("Authenticated as " + data.user.email);
        });

      $http.get('/api/0/projects/')
        .success(function(data){
          $scope.projectList = data;
        });

      $rootScope.$watch('pageTitle', function(value) {
        $document.title = value;
      });

      $rootScope.$on('$routeChangeError', function(e, current, previous){
        flash('error', 'There was an error loading the page you requested :(');
      });

      $('.navbar .container').show();
    }]);
  });
})();
