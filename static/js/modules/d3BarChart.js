define([
  "angular",
  "d3",
  "d3-tip",
  "jquery"
], function(angular, d3, d3tip, $) {
  'use strict';

  function timeSeriesChart() {
    var margin = {top: 0, right: 0, bottom: 0, left: 0},
      width = 760,
      height = 120,
      chartHeight = height - margin.top - margin.bottom,
      chartWidth = width - margin.left - margin.right,
      barWidth,
      timeFormat = d3.time.format("%b %d"),
      xDomain,
      yDomain,
      xValue = function(d) { return d[0]; },
      yValue = function(d) { return d[1]; },
      xScale = d3.time.scale(),
      yScale = d3.scale.linear(),
      yAxis = d3.svg.axis().scale(yScale)
        .orient("left"),
      xAxis = d3.svg.axis().scale(xScale)
        .orient("bottom")
        .ticks(d3.time.month, 1)
        .tickFormat(timeFormat);

    function chart(selection) {
      selection.each(function(data) {
        // Convert data to standard representation greedily;
        // this is needed for nondeterministic accessors.
        data = data.map(function(d, i) {
          return [xValue.call(data, d, i), yValue.call(data, d, i)];
        });

        $(this).height(height);
        $(this).width(width);

        width = $(this).width();
        height = $(this).height();
        chartHeight = height - margin.top - margin.bottom;
        chartWidth = width - margin.left - margin.right;
        barWidth = (width - data.length) / data.length;

        xDomain = d3.extent(data, function(d) { return d[0]; });
        yDomain = [0, d3.max(data, function(d) { return d[1]; })];

        // Update the x-scale.
        xScale
          .domain(xDomain)
          .range([0, chartWidth - barWidth]);

        // Update the y-scale
        yScale
          .domain(yDomain)
          .range([chartHeight, 0]);

        yAxis
          .ticks(2);

        var tip = d3tip()
          .attr('class', 'd3-tip')
          .offset([-10, 0])
          .html(function(d) {
            return '<small>' + timeFormat(d[0]) + '</small><br>' +
              d[1];
          });

        var svg = d3.select(this).append("svg:svg")
          .attr("width", width)
          .attr("height", height)
        .append("g")
          .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        svg.call(tip);

        svg.selectAll(".bar")
          .data(data)
        .enter().append("rect")
          .attr("class", "bar")
          .attr("x", X)
          .attr("y", Y)
          .attr("width", function(d) { return barWidth; })
          .attr("height", function(d) { return height - yScale(d[1]); })
          .on('mouseover', tip.show)
          .on('mouseout', tip.hide);
      });
    }

    // The x-accessor for the path generator; xScale ∘ xValue.
    function X(d, i) {
      return xScale(d[0]);
    }

    // The y-accessor for the path generator; yScale ∘ yValue.
    function Y(d) {
      return yScale(d[1]);
    }

    chart.margin = function(_) {
      if (!arguments.length) return margin;
      margin = _;
      return chart;
    };

    chart.width = function(_) {
      if (!arguments.length) return width;
      width = _;
      return chart;
    };

    chart.height = function(_) {
      if (!arguments.length) return height;
      height = _;
      return chart;
    };

    chart.x = function(_) {
      if (!arguments.length) return xValue;
      xValue = _;
      return chart;
    };

    chart.y = function(_) {
      if (!arguments.length) return yValue;
      yValue = _;
      return chart;
    };

    return chart;
  }

  var defaultOptions = {
    width: '100%',
    height: '120'
  };

  angular.module('changes.barchart', [])
    .directive('d3barchart', function($window, $timeout) {
      /**
       $scope.chartData = [[x, y], [x, y]];

       <barchart ng-model="chartData"/>
       */
      function BarChart(element, items, options) {
        var self = this;

        self.options = $.extend({}, defaultOptions, options || {});

        self.chart = timeSeriesChart()
            .x(function(d) { return new Date(d.time); })
            .y(function(d) { return d.value; })
            .width(self.options.width)
            .height(self.options.height);

        d3.select(element.get(0))
            .datum(items)
            .call(self.chart);
      }

      return {
        restrict: 'E',
        link: function(scope, elem, attrs) {
          function render(data, attrs){
            $(elem).empty();
            new BarChart(elem, data, attrs);
          }

          scope.$watch(attrs.ngModel, function(value) {
            $timeout(function(){
              if (!value) {
                return;
              }
              render(value, attrs);
            });
          });
        }
      };
  });
});
