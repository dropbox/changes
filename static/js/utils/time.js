define([], function() {
  'use strict';

  function round(value) {
    return parseInt(value * 100, 10) / 100;
  }

  return {
    duration: function duration(value) {
      var result, neg;

      neg = value < 0 ? true : false;
      if (neg) {
        value = -value;
      }

      if (value > 7200000) {
        result = Math.round(value / 3600000) + ' hr';
      } else if (value > 120000) {
        result = Math.round(value / 60000) + ' min';
      } else if (value > 10000) {
        result = Math.round(value / 1000) + ' sec';
      } else if (value > 1000) {
        result = round(value / 1000) + ' sec';
      } else {
        result = Math.round(value) + ' ms';
      }

      if (neg) {
        result = '-' + result;
      }

      return result;
    }
  };
});
