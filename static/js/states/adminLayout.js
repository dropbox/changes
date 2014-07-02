define([
  'app'
], function(app) {
  'use strict';

  return {
    abstract: true,
    url: '/admin/',
    templateUrl: 'partials/admin/layout.html',
    controller: function($scope, $rootScope, $location, $window, authData, flash, PageTitle) {
      if (!authData.user.isAdmin) {
        return $location.path('/');
      }

      PageTitle.set('Changes Admin');

      $scope.appVersion = $window.APP_VERSION;
      $scope.user = authData.user;
      $scope.authenticated = authData.authenticated;

      $rootScope.$on('$stateChangeError', function(event, toState, toParams, fromState, fromParams, error){
        flash('error', 'There was an error loading the page you requested :(');
        // this should really be default behavior
        throw error;
      });

      $('.navbar .container').show();
    },
    resolve: {
      // TODO: move auth into service
      authData: function($http) {
        return $http.get('/api/0/auth/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
