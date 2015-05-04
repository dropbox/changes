define([
  'app'
], function(app) {
  'use strict';

  return {
    url: '/404/:original_url/',
    templateUrl: 'partials/fourohfour.html',
    controller: function($scope, $location, $stateParams) {
      // see comment in routes.js about using base64 encoding
      $scope.original_url = atob(
        $stateParams.original_url.replace("-", "/")
      );
    }
  };
});
