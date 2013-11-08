define([], function() {
  var chart_defaults = {
    limit: 50,
    linkFormatter: function(item) {
      return item.link;
    }
  };

  return {
    getChartData: function getChartData(items, current, options) {
      // this should return two series, one with passes, and one with failures
      var options = $.extend({}, chart_defaults, options || {}),
          data = new Array(options.limit),
          current = current || null,
          i, y;

      if (current) {
        items = $.merge([], items);
        items.pop();
        items.unshift(current);
      }

      var data = [];
      for (i = 0, y = options.limit; (item = items[i]) && y > 0; i++, y--) {
        data.push({
          value: item.duration || 50,
          className: 'result-' + item.result.id,
          id: item.id,
          data: item,
          highlight: current && current.id == item.id
        });
      }

      return {
        data: data,
        options: options
      }
    }
  }
});
