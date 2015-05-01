define([
  'app'
], function(app) {
  'use strict';

  // Install a named controller so that we can also use it from tests
  app.controller('AdminMessageListCtrl',
      function($scope, $state, $stateParams, adminMessageData) {
        $scope.messageData = adminMessageData;
  });

  return {
    parent: 'admin_layout',
    url: 'messages/',
    templateUrl: 'partials/admin/message-list.html',
    controller: 'AdminMessageListCtrl',
    resolve: {
      adminMessageData: function($http) {
        return $http.get('/api/0/messages/').then(function(response){
          return response.data;
        });
      }
    }
  };
});
