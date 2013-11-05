define(['app'], function(app) {
  function round(value) {
    return parseInt(value * 100, 10) / 100;
  }

  return function duration(value) {
    var result;

    if (value > 7200000) {
      result = round(value / 3600000) + ' hr';
    } else if (value > 120000) {
      result = round(value / 60000) + ' min';
    } else if (value > 1000) {
      result = round(value / 1000) + ' sec';
    } else {
      result = parseInt(value, 10) + ' ms';
    }

    return result;
  }
});
