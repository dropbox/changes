(function(){
  'use strict';

  define(['app', 'modules/notify', 'modules/flash'], function(app) {
    app.controller('layoutCtrl', [
        '$scope', '$rootScope', '$location', '$http', '$document', 'notify', 'flash', 'stream',
        function($scope, $rootScope, $location, $http, $document, notify, flash, Stream) {

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

      $scope.projectList = [];
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

      $scope.$on('$routeChangeSuccess', function(){
        $scope.navPath = getNavPath();
        $scope.projectSearchQuery = $location.search();

        $rootScope.pageTitle = 'Changes';
        $rootScope.activeProject = null;
      });

      $http.get('/api/0/auth/')
        .success(function(data){
          $scope.authenticated = data.authenticated;
          $scope.user = data.user || {};

          notify("Authenticated as " + data.user.email);

          var stream = new Stream($scope, '/api/0/authors/me/builds/');
          stream.subscribe('build.update', notifyBuild);

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
