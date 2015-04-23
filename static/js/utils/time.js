define(['moment'], function(moment) {
  'use strict';

  function round(value) {
    return parseInt(value * 100, 10) / 100;
  }

  return {
    duration: function(value) {
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
    },

    timeSince: function(timestamp, currentTimestamp) {
      var date = moment.utc(timestamp),
          diff = date.diff(currentTimestamp),
          past = diff > 0,
          result, value;

      diff = Math.abs(diff);

      if (diff > 1728000000) { // 48 hours
        return date.format('l');
      } else if (diff > 7200000) {
        value = Math.round(diff / 3600000);
        result = value + ' hour';
      } else if (diff > 60000) {
        value = Math.round(diff / 60000);
        result = value + ' minute';
      } else {
        return 'just now';
      }

      if (value != 1) {
        result = result + 's';
      }

      if (past) {
        return 'in ' + result;
      }
      return result + ' ago';
    }
  };
});
