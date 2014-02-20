define(['app'], function(app) {
  'use strict';

  app.controller('planListCtrl', ['initial', '$scope', 'collection', function(initial, $scope, Collection) {
    $scope.plans = new Collection($scope, initial.data);
  }]);
});
