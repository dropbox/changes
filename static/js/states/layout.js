define([
  'app'
], function(app) {
  'use strict';

  return {
    abstract: true,
    templateUrl: 'partials/layout.html',
    controller: function($scope, $rootScope, $location, $http, $document, projectList, notify, flash, stream) {
      function notifyBuild(build) {
        if (build.status.id == 'finished') {
          var msg = 'Build <a href="/builds/' + build.id + '/">#' + build.number + '</a> (' + build.project.name + ') ' + build.result.name + ' &mdash; ' + build.target;
          notify(msg, build.result.id == 'failed' ? 'error' : 'success');
        }
      }

      function getNavPath() {
        if (!$rootScope.activeProject) {
          return;
        }

        var urlBase = '/projects/' + $rootScope.activeProject.slug + '/';
        switch ($location.path()) {
          case urlBase:
          case urlBase + 'search/':
            return 'builds';
          case urlBase + 'commits/':
            return 'commits';
          case urlBase + 'tests/':
            return 'tests';
          case urlBase + 'stats/':
            return 'stats';
        }

      }

      $rootScope.pageTitle = 'Changes';

      $scope.projectList = projectList.data;
      $scope.authenticated = null;
      $scope.user = null;
      $scope.navPath = null;
      $scope.projectSearchQuery = {
        query: null,
        source: null
      };

      $scope.searchBuilds = function(){
        if (!$rootScope.activeProject) {
          return false;
        }

        if (!this.projectSearchQuery) {
          $location.path('/projects/' + $rootScope.activeProject.slug + '/').search({});
        } else {
          $location.path('/projects/' + $rootScope.activeProject.slug + '/search/').search(this.projectSearchQuery);
        }

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

      $http.get('/api/0/auth/')
        .success(function(data){
          $scope.authenticated = data.authenticated;
          $scope.user = data.user || {};

          if (data.user) {
            notify("Authenticated as " + data.user.email);

            // TODO(dcramer): enable this once we solve concurrent subscriptions
            // var stream = new Stream($scope, '/api/0/authors/me/builds/');
            // stream.subscribe('build.update', notifyBuild);
          }
        });

      $rootScope.$watch('pageTitle', function(value) {
        $document.title = value;
      });

      $rootScope.$watch('activeProject', function(){
        $scope.navPath = getNavPath();
      });

      $rootScope.$on('$stateChangeError', function(event, toState, toParams, fromState, fromParams, error){
        console.log(error);
        flash('error', 'There was an error loading the page you requested :(');
      });

      $('.navbar .container').show();
    },
    resolve: {
      projectList: function($http) {
        return $http.get('/api/0/projects/');
      }
    }
  };
});
