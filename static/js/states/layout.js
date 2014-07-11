define([
  'app'
], function(app) {
  'use strict';

  return {
    abstract: true,
    templateUrl: 'partials/layout.html',
    controller: function($scope, $rootScope, $location, $window, authData, projectList, flash, PageTitle) {
      PageTitle.set('Changes');

      $scope.appVersion = $window.APP_VERSION;
      $scope.projectList = projectList.data;
      $scope.user = authData.user;
      $scope.activeUser = $scope.user;
      $scope.authenticated = authData.authenticated;
      $scope.projectSearchQuery = {
        query: null,
        source: null
      };

      $scope.searchBuilds = function(){
        if (!$rootScope.activeProject) {
          return false;
        }

        $location.path('/projects/' + $rootScope.activeProject.slug + '/builds/').search(this.projectSearchQuery);

        return false;
      };

      // TODO: this should be replaced w/ project inheritance
      $scope.$on('$stateChangeSuccess', function(_u1, _u2, $stateParams){
        $scope.projectSearchQuery = $location.search();

        if (!$stateParams.project_id) {
          $rootScope.activeProject = null;
        } else if ($rootScope.activeProject && $stateParams.project_id != $rootScope.activeProject.slug) {
          $rootScope.activeProject = null;
        }
      });

      $rootScope.$on('$stateChangeError', function(event, toState, toParams, fromState, fromParams, error){
        flash('error', 'There was an error loading the page you requested :(');
        // this should really be default behavior
        throw error;
      });

      $('.navbar .container').show();
    },
    resolve: {
      projectList: function($http) {
        return $http.get('/api/0/projects/');
      },
      // TODO: move auth into service
      authData: function($http) {
        return $http.get('/api/0/auth/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
