define([
  'app',
  'moment',
  'utils/duration'
], function(app, moment, duration) {
  'use strict';

  return {
    parent: 'project_details',
    url: 'tests/?parent',
    templateUrl: 'partials/project-test-list.html',
    controller: function($http, $scope, $state, $stateParams, projectData, testGroupData) {
      var chart_options = {
        tooltipFormatter: function(data, item) {
          return '<div style="width:80px;text-align:center">' +
              item.value + '<br>' +
              '<small>' + moment(item.time).format('l') + '</small>' +
            '</div>';
        }
      };

      function loadTestList(url) {
        if (!url) {
          return;
        }
        $http.get(url)
          .success(function(data, status, headers){
            $scope.testGroupList = data.groups;
            $scope.trail = data.trail;
          });
      }

      $scope.selectChart = function(chart) {
        $scope.selectedChart = chart;
        $http.get('/api/0/projects/' + projectData.id + '/stats/?resolution=1w&points=52&stat=' + chart).success(function(data){
          var chartData = [];
          $.each(data, function(_, node){
            chartData.push([node.time / 1000, node.value]);
          });
          $scope.chartData = chartData;
        });
      };

      $scope.selectChart('test_count');

      $scope.chartData = null;
      $scope.testGroupList = testGroupData.data.groups;
      $scope.trail = testGroupData.data.trail;
    },
    resolve: {
      testGroupData: function($http, $stateParams, projectData) {
        return $http.get('/api/0/projects/' + projectData.id + '/testgroups/?parent=' + ($stateParams.parent || ''));
      }
    }
  };
});
