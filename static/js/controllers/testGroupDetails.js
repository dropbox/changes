define(['app', 'directives/timeSince', 'directives/duration'], function(app) {
  app.controller('testGroupDetailsCtrl', ['$scope', 'initialData', '$routeParams', function($scope, initialData, $routeParams) {
    'use strict';

    var stream,
        entrypoint = '/api/0/testgroups/' + $routeParams.testgroup_id + '/';

    function getTestFullName(test) {
        if (test.package) {
            return test.package + '.' + test.name;
        } else {
            return test.name;
        }
    }

    $.each(initialData.data.childTests, function(_, test){
        test.fullName = getTestFullName(test);
    });
    $.each(initialData.data.testFailures, function(_, test){
        test.fullName = getTestFullName(test);
    });

    $scope.build = initialData.data.build;
    $scope.testFailures = initialData.data.testFailures;
    $scope.testGroup = initialData.data.testGroup;
    $scope.childTestGroups = initialData.data.childTestGroups;
    $scope.childTests = initialData.data.childTests;
  }]);
});
