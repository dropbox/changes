define(['flot', 'utils/duration'], function(flot, duration) {
  'use strict';

  angular.module('flot', [])
    .directive('chart', [function() {
      return {
        restrict: 'E',
        link: function(scope, elem, attrs) {
          var data = scope[attrs.ngModel],
              options = {
                grid: {
                    show: true,
                    hoverable: true,
                    backgroundColor: '#ffffff',
                    borderColor: '#DEE3E9',
                    borderWidth: 2,
                    tickColor: '#DEE3E9'
                },
                xaxis: {
                  show: false,
                },
                yaxis: {
                  tickFormatter: function (val, axis) {
                    return Math.round(val / 1000 * 100) / 100 + ' sec';
                  }
                },
                hoverable: false,
                legend: {
                  show: false
                },
                tooltip: true,
                tooltipOpts: {
                  content: '%s - %y'
                },
                series: {
                  bars: {
                    show: true,
                    lineWidth: 2,
                    barWidth: 0.9,
                    align: 'center'
                  },
                  stack: true,
                  shadowSize: 0
                },
                colors: ['#c7c0de', '#58488a']
              };

          $.plot(elem, data, options);
        }
      };
  }]);
});

