define([
  'angular',
  'jquery',
  'bootstrap/tooltip'
], function(angular, $, tooltip_func) {
  'use strict';

  angular.module('barChart', [])
    .directive('barchart', ['$window', function($window) {
      var default_options = {
        tooltipFormatter: function(data, item) {
          return item.value;
        },
        linkFormatter: function(data, item) {
          return null;
        },
        limit: 50
      };

      function getTooltipContent(barchart, item) {
        var content = '';

        content += '<div class="barchart-tip">';
        content += barchart.options.tooltipFormatter(item.data, item);
        content += '</div>';

        return content;
      }

      function BarChart(element, items, options) {
        var self = this;

        self.options = $.extend({}, default_options, options || {});
        self.parent = $(element);
        self.el = $('<ul class="barchart"></ul>');
        self.maxValue = 0;
        self.nodeWidthPercent = parseInt(100 / options.limit, 10);

        // find initial maxValue
        $.each(items, function(_, item) {
          if (item.value > self.maxValue) {
            self.maxValue = item.value;
          }
        });

        $.each(items, function(_, item){
          self.addItem(item);
        });

        self.parent.html(self.el);
      }

      BarChart.prototype.addItem = function addItem(item) {
        // {value: 50, className: 'result-failed', id: 1, data: {}, highlight: false}
        var node = $('<li></li>'),
            percent, innerNode, link;

        if (item.value > this.maxValue) {
          // TODO: this would require us to recompute the height of all nodes
        }

        percent = parseInt(item.value / this.maxValue * 100, 10);

        node.data({
          value: item.value,
          id: item.id
        });

        node.css({
          width: this.nodeWidthPercent + '%'
        });

        if (item.highlight === true) {
          node.addClass('active');
        }

        if (item.className !== undefined) {
          node.addClass(item.className);
        }

        innerNode = $('<a>' +
          '<span class="label"></span>' +
          '<span class="count" style="height:' + percent + '%">' + item.value + '</span>' +
        '</a>');

        link = this.options.linkFormatter(item.data, item);
        if (link) {
          innerNode.attr({
            href: link
          });
        }

        innerNode.attr('data-title', getTooltipContent(this, item));
        innerNode.attr('title', getTooltipContent(this, item));
        innerNode.attr('data-placement', 'bottom');
        innerNode.attr('data-html', 'true');

        // Because we use angular, jquery, bootstrap, and requirejs, we're in
        // this situation where there are multiple jquery objects floating
        // around, not all of them augmented with bootstrap. The solution is to
        // explicitly include bootstrap functions and call them directly via
        // bind. Make sure to use data attributes over jquery.data, as each
        // jquery has its own data store.
        //
        // There are internet fixes for requirejs/jquery/bootstrap, but none for
        // all four libraries (angular has its own relation with jquery.)
        tooltip_func.bind(innerNode)();

        node.append(innerNode);

        this.el.append(node);
      };


      return {
        restrict: 'E',
        link: function(scope, elem, attrs) {
          scope.$watchCollection(attrs.data, function(value) {
            new BarChart(elem, value || [], scope.$eval(attrs.options) || {});
          });
        }
      };
  }]);
});
