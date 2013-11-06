define([], function() {
  var chart_defaults = {
    limit: 50,
    labelFormatter: function(item) {
      return item.id;
    },
    linkFormatter: function(item) {
      return null;
    }
  };

  return {
    getChartData: function getChartData(items, current, options) {
      // this should return two series, one with passes, and one with failures
      var options = $.extend({}, chart_defaults, options || {}),
          ok = new Array(options.limit),
          failures = new Array(options.limit),
          skipped = new Array(options.limit),
          unknown = new Array(options.limit),
          points = {},
          test, point, i, y,
          current = current || null;

      if (current) {
        items = $.merge([], items);
        items.pop();
        items.unshift(current);
      }

      for (i = 0, y = options.limit; (item = items[i]) && y > 0; i++, y--) {
        points[y] = item;
        point = [y, item.duration || 1];
        if (item.result.id == 'passed') {
          ok[y] = point;
        } else if (item.result.id == 'skipped') {
          skipped[y] = point;
        } else if (item.result.id == 'aborted' || item.result.id == 'unknown') {
          unknown[y] = point;
        } else {
          failures[y] = point;
        }
      }

      var itemLabelFormatter = function(xval, yval, flotItem) {
        return options.labelFormatter(points[xval]);
      };
      var itemLinkFormatter = function(xval, yval, flotItem) {
        return options.linkFormatter(points[xval]);
      };

      return {
        values: [
          {data: ok, color: '#5cb85c', label: 'Passed'},
          {data: failures, color: '#d9322d', label: 'Failed'},
          {data: skipped, color: 'rgb(255, 215, 0)', label: 'Skipped'},
          {data: unknown, color: '#aaaaaa', label: 'Unknown'}
        ],
        options: {
          labelFormatter: itemLabelFormatter,
          linkFormatter: itemLinkFormatter
        }
      }
    }
  }
});
