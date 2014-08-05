define([
  'app'
], function(app) {
  'use strict';

  // Install a named controller so that we can also use it from tests
  app.controller('AdminLayoutCtrl', function($scope, $rootScope, $location, $window, authData, flash, PageTitle) {
    // User isn't logged in - redirect to login
    if (!authData || !authData.user) {
      console.log("User not identified - redirecting to login");
      $window.location.href = '/auth/login/';
      return;
    }
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
  });

  return {
    abstract: true,
    url: '/admin/',
    templateUrl: 'partials/admin/layout.html',
    controller: 'AdminLayoutCtrl',
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
