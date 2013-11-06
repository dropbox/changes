define(['flot', 'utils/duration'], function(flot, duration) {
  'use strict';

  angular.module('flot', [])
    .directive('chart', ['$window', function($window) {
      var default_options = {
        labelFormatter: function(xval, yval, flotItem) {
          return null;
        },
        linkFormatter: function(xval, yval, flotItem) {
          return null;
        },
        grid: {
            show: true,
            clickable: true,
            hoverable: true,
            backgroundColor: '#ffffff',
            borderColor: '#DEE3E9',
            borderWidth: 2,
            tickColor: '#DEE3E9'
        },
        xaxis: {
          tickSize: 1,
          min: 0,
          tickColor: '#ffffff',
          tickFormatter: function() { return ''; }
        },
        yaxis: {
          tickFormatter: function (val, axis) {
            return Math.round(val / 1000 * 100) / 100 + ' sec';
          },
          min: 0
        },
        hoverable: false,
        legend: {
          show: false
        },
        tooltip: true,
        tooltipOpts: {},
        series: {
          bars: {
            show: true,
            lineWidth: 1,
            barWidth: 0.9,
            align: 'center'
          },
          stack: true,
          shadowSize: 0
        },
        colors: ['#c7c0de', '#58488a']
      };

      return {
        restrict: 'E',
        link: function(scope, elem, attrs) {
          var data = scope[attrs.ngModel],
              points = {},
              options,
              label_cache = {};

          function render(data){
            label_cache = {};

            options = $.extend({}, default_options, data.options || {});
            options.tooltipOpts.content = function(label, xval, yval, flotItem) {
              var retval = label_cache[[xval, yval]];
              if (retval === undefined) {
                retval = options.labelFormatter(xval, yval, flotItem) + '<br>' + label + ' &mdash; ' + options.yaxis.tickFormatter(yval);
                label_cache[[xval, yval]] = retval;
              }
              return retval;
            };

            $.plot(elem, data.values, options);
          }

          $(elem).bind("plotclick", function(e, pos, item) {
            var link = options.linkFormatter(item.datapoint[0], item.datapoint[1], item);
            if (link) {
              $window.location.href = link;
            }
          });

          scope.$watch(attrs.ngModel, function(value) {
            render(value);
          });
        }
      };
  }]);
});

