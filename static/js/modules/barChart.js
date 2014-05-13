define(['jquery', 'angular', 'bootstrap'], function($) {
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

        innerNode.data({
          title: getTooltipContent(this, item),
          placement: 'bottom',
          html: true
        });

        innerNode.tooltip();

        node.append(innerNode);

        this.el.append(node);
      };


      return {
        restrict: 'E',
        link: function(scope, elem, attrs) {
          var options,
              label_cache = {};

          function render(data, options){
            new BarChart(elem, data, options);
          }

          scope.$watch(attrs.ngModel, function(value) {
            if (value) {
              render(value.data, value.options);
            } else {
              render([], {});
            }
          });
        }
      };
  }]);
});
