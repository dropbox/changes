define([
    'app'
], function(app) {
    'use strict';

    return {
        parent: 'project_details',
        url: 'flaky_tests/',
        templateUrl: 'partials/project-flaky-tests.html',
        controller: function($scope, projectData, flakyTestsData) {
            $scope.lastUpdate = flakyTestsData.lastUpdate;
            $scope.flakyTests = flakyTestsData.flakyTests;
        },
        resolve: {
            flakyTestsData: function($http, $stateParams, projectData) {
                var url = '/api/0/projects/' + projectData.id + '/flaky_tests/';
                return $http.get(url).then(function(response) {
                    return response.data;
                });
            }
        }
    };
});
