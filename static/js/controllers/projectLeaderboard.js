(function(){
  'use strict';

  define([
      'app',
      'utils/chartHelpers',
      'utils/duration',
      'utils/escapeHtml',
      'utils/sortBuildList',
      'nvd3'], function(app, chartHelpers, duration, escapeHtml, sortBuildList) {
    app.controller('projectLeaderboardCtrl', [
        '$scope', '$rootScope', 'initialProject', 'initialStats', '$http', '$routeParams', 'stream',
        function($scope, $rootScope, initialProject, initialStats, $http, $routeParams, Stream) {
        var bs = initialStats.data.buildStats;

        if (bs.numBuilds > 0) {
          bs.percentPassed = Math.round(bs.numPassed / (bs.numFailed + bs.numPassed) * 100);
        } else {
          bs.percentPassed = null;
        }

        if (bs.previousPeriod.numBuilds > 0) {
          bs.previousPeriod.percentPassed = Math.round(bs.previousPeriod.numPassed / (bs.previousPeriod.numFailed + bs.previousPeriod.numPassed) * 100);
        } else {
          bs.previousPeriod.percentPassed = null;
        }

        if (bs.avgBuildTime && bs.previousPeriod.avgBuildTime) {
          bs.buildTimeChange = bs.avgBuildTime - bs.previousPeriod.avgBuildTime;
        } else {
          bs.buildTimeChange = null;
        }

        $scope.buildStats = bs;
        $scope.newSlowTestGroups = initialStats.data.newSlowTestGroups;
        $scope.project = initialProject.data;

        $rootScope.activeProject = $scope.project;

        nv.addGraph(function() {
             var chart = nv.models.multiBarChart()
                           .showControls(false)
                           .stacked(true)
                           .color(['#5cb85c', '#d9534f', '#aaaaaa'])
                           .margin({top: 0, right: 30, bottom: 20, left: 30});

            chart.xAxis.tickFormat(function(d) {
              return d3.time.format('%x')(new Date(d * 1000));
            });

            chart.yAxis
              .tickFormat(d3.format(',f'));

            d3.select('#chart svg')
              .datum(getChartData())
              .transition().duration(500).call(chart);

            nv.utils.windowResize(chart.update);

            return chart;
        });


        $scope.buildHistory = initialStats.data.buildHistory;

        function getChartData() {
          var data = [
            {
              "key": "Passed",
              "values": []
            },
            {
              "key": "Failed",
              "values": []
            },
            {
              "key": "Aborted",
              "values": []
            }
          ];

          $.each($scope.buildHistory, function(timestamp, result) {
            data[0].values.push([timestamp, result.counts.passed]);
            data[1].values.push([timestamp, result.counts.failed]);
            data[2].values.push([timestamp, result.counts.aborted]);
          });

          return data.map(function(series) {
            series.values = series.values.map(function(d) {
              return {x: d[0], y: d[1]};
            });
            return series;
          });
        }
    }]);
  });
})();
