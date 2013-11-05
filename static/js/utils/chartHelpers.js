define([], function() {
  return {
    getChartData: function getChartData(items, limit) {
      // this should return two series, one with passes, and one with failures
      var ok = [],
          failures = [],
          skipped = [],
          unknown = [],
          test, point, i, y,
          limit = limit || 50;

      for (i = items.length - 1, y = 0; (item = items[i]) && y < limit; i--, y++) {
        point = [i, item.duration || 1];
        if (item.result.id == 'passed') {
          ok.push(point);
        } else if (item.result.id == 'skipped') {
          skipped.push(point);
        } else if (item.result.id == 'aborted' || item.result.id == 'unknown') {
          unknown.push(point);
        } else {
          failures.push(point);
        }
      }

      return {
        values: [
          {data: ok, color: '#c7c0de', label: 'Passed'},
          {data: failures, color: '#d9322d', label: 'Failed'},
          {data: skipped, color: 'rgb(255, 215, 0)', label: 'Skipped'},
          {data: unknown, color: '#aaaaaa', label: 'Unknown'}
        ],
        options: {}
      }
    }
  }
});
