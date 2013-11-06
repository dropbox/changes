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
            borderWidth: 1,
            tickColor: '#eeeeee',
            margin: {right: 0}
        },
        xaxis: {
          tickSize: 1,
          min: 0,
          tickColor: 'transparent',
          tickFormatter: function() { return ''; }
        },
        yaxis: {
          ticks: 3,
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

            options = $.extend(true, {}, default_options, data.options || {});
            options.tooltipOpts.content = function(label, xval, yval, flotItem) {
              var retval = label_cache[[xval, yval]];
              if (retval === undefined) {
                retval = options.labelFormatter(xval, yval, flotItem) + '<br>' + label + ' &mdash; ' + options.yaxis.tickFormatter(yval);
                label_cache[[xval, yval]] = retval;
              }
              return retval;
            };

            // find max value
            var max = 0;
            $.each(data.values, function(_, series){
              console.log(series.data);
              $.each(series.data, function(_, point){
                if (point && point[1] > max) {
                  max = point[1];
                }
              });
            });

            var ticks = [[0, '']],
                per_step = max / (options.yaxis.ticks + 1),
                value, i;
            for (i = 0; i < options.yaxis.ticks; i++) {
              value = (i + 1) * per_step;
              ticks.push([value, options.yaxis.tickFormatter(value)]);
            }

            console.log(ticks);

            options.yaxis.ticks = ticks

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

