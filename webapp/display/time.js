import React from 'react';
import moment from 'moment';

import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

/*
 * Contains a bunch of components for dealing with time. We also use the
 * moment library. Some notes:
 * - new Date().getTime() uses local time in firefox and utc time in chrome.
 *   So its better to avoid this in favor of moment.utc.
 * - We assume that all timestamps from the server/api are utc. We may
 *   want to display them using local time, though.
 */

// 1 class (TimeText), 1 function (display_duration)

/*
 * Renders times, usually for tables. We do something similar to gmail:
 *  If today: 2:35pm, 11:22am
 *  If another day: May 11, April 5
 *  If another year: Feb 13, 2008
 * Timestamps aren't relative, so no need for live updates...
 *  TODO: do we need times for builds that aren't today? Also consider days
 *  of week?
 *  TODO: add 24 hour format support
 *  TODO: title with exact time? in UTC?
 */
export var TimeText = React.createClass({

  propTypes: {
    // The time to show. If not ISO 8601, will do the same as new Date()
    time: proptype.string.isRequired,
    // Manually specify time format. unix timestamp is example of when this is
    // needed (format='X', see http://momentjs.com/docs/#/parsing/string-format/)
    format: proptype.string,

    // ...
    // transfers other properties to rendered <span />
  },

  getDefaultProps: function() {
    return {
      'format': ''
    }
  },

  render: function() {
    var { time, format, ...others } = this.props;
    var time_text = '';
    if (time) {
      // parse in utc, display in local time
      if (format) {
        var time = moment.utc(time, format).local();
      } else {
        var time = moment.utc(time).local();
      }
      var now = moment();
      var is_same_year = time.year() === now.year();
      var is_same_day = time.format('MMMDDDYY') === now.format('MMMDDDYY');
      if (is_same_day) {
        time_text = time.format('h:mm a');
      } else if (is_same_year) {
        time_text = time.format('MMM D');
      } else {
        time_text = time.format('MMM D, YYYY');
      }
    }
    return <span {...others}>{time_text}</span>;
  }
});

/*
 * Converts 136 [in seconds] to a string like "2m16s"
 */
export var display_duration = function(total_seconds) {
  return display_duration_pieces(total_seconds).join("");
}

/*
 * as display_duration, but returns a 4-tuple of durations. Useful if you
 * want to emphasize hour/day
 */
export var display_duration_pieces = function(total_seconds) {
  if (total_seconds < 1) {
    return [null, null, null, "<1s"];
  }

  var seconds = 0, minutes = 0, hours = 0, days = 0;
  minutes = Math.floor(total_seconds / 60);
  seconds = Math.floor(total_seconds % 60);

  if (minutes > 60) {
    hours = Math.floor(minutes / 60);
    minutes = minutes % 60;
  }

  if (hours > 24) {
    days = Math.floor(hours / 24);
    hours = hours % 24;
  }

  return [
    (days ? `${days}d` : null),
    (hours ? `${hours}h` : null),
    (minutes ? `${utils.pad(minutes)}m` : null),
    `${minutes ? utils.pad(seconds, 2) : seconds}s`
  ];
}
