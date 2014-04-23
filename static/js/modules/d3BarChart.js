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
      xValue = function(d) { return d[0]; },
      yValue = function(d) { return d[1]; },
      xScale = d3.time.scale(),
      yScale = d3.scale.linear(),
      yAxis = d3.svg.axis().scale(yScale).orient("left"),
      xAxis = d3.svg.axis().scale(xScale).orient("bottom").tickSize(0, 0);

    function chart(selection) {
      selection.each(function(data) {

        $(this).height(height);
        $(this).width(width);

        width = $(this).width();
        height = $(this).height();

        // Convert data to standard representation greedily;
        // this is needed for nondeterministic accessors.
        data = data.map(function(d, i) {
          return [xValue.call(data, d, i), yValue.call(data, d, i)];
        });

        var max_y = d3.max(data, function(d) { return d[1]; });

        // Update the x-scale.
        xScale
          // .domain(data.map(function(d) { return d[0]; }))
          .domain([data[0][0], data[data.length - 1][0]])
          .rangeRound([0, width - margin.left - margin.right]);

        // Update the y-scale
        yScale
          .domain([0, max_y])
          .range([height - margin.top - margin.bottom, 0]);


        yAxis.tickValues([0, max_y]);

        var tip = d3tip()
          .attr('class', 'd3-tip')
          .offset([-10, 0])
          .html(function(d) {
              return d[1] + '<br><small>' + d[0] + '</small>';
          });

        var svg = d3.select(this).append("svg")
          .attr("width", width)
          .attr("height", height)
        .append("g")
          .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        svg.call(tip);

        // svg.append("g")
        //     .attr("class", "y axis")
        //     .call(yAxis)

        svg.selectAll(".bar")
          .data(data)
        .enter().append("rect")
          .attr("class", "bar")
          .attr("x", X)
          .attr("y", Y)
          .attr("width", function(d) { return (width / (data.length + 1)) - 1; })
          .attr("height", function(d) { return height - yScale(d[1]); })
          .on('mouseover', tip.show)
          .on('mouseout', tip.hide);
      });
    }

    // The x-accessor for the path generator; xScale ∘ xValue.
    function X(d) {
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
            .x(function(d) { return new Date(d[0] * 1000); })
            .y(function(d) { return d[1]; })
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
