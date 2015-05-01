define(['app'], function(app) {
  'use strict';

  /**
   * Reduces the message down to only the items required when posting message
   *  updates to the Changes API.
   *
   * @param messageData: Full admin message data to reduce.
   * @returns {{message: *}} Reduced admin message data.
   */
  function _getFormData(messageData) {
    var messageToReturn = '';
    if (messageData) {
      messageToReturn = messageData.message;
    }

    return {
      // Only include the message because the API sets all other parameters
      message: messageToReturn
    };
  }

  // Install a named controller so that we can also use it from tests
  app.controller('AdminMessageDetailsCtrl',
      function($http, $scope, adminMessageData, flash) {
      $scope.messageData = adminMessageData;
      $scope.formData = _getFormData(adminMessageData);

      $scope.saveForm = function() {
        $http.post('/api/0/messages/', $scope.formData).success(function(data) {
          $scope.messageData = data;
          $scope.formData = _getFormData(data);
          $scope.messageDetailsForm.$setPristine();

          if (data.message) {
            flash('success', 'Message saved successfully.');
          } else {
            flash('success', 'Message removed successfully.');
          }
        })
        .error(function() {
          flash('error', 'An error occurred, and we have yet to implement a way to tell you about it.');
        });
      };
  });

  return {
    parent: 'admin_layout',
    url: 'messages/:message_id/',
    templateUrl: 'partials/admin/message-details.html',
    controller: 'AdminMessageDetailsCtrl',
    resolve: {
      adminMessageData: function($http) {
        return $http.get('/api/0/messages/').then(function(response) {
          return response.data;
        });
      }
    }
  };
});
