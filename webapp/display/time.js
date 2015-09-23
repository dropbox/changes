import React, { PropTypes } from 'react';
import moment from 'moment';

import Examples from 'es6!display/examples';

import * as utils from 'es6!utils/utils';

/*
 * Contains a bunch of components for dealing with time. We also use the
 * moment library. Some notes:
 * - new Date().getTime() uses local time in firefox and utc time in chrome.
 *   So its better to avoid this in favor of moment.utc.
 * - We assume that all timestamps from the server/api are utc. We may
 *   want to display them using local time, though.
 */

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
    time: PropTypes.string.isRequired,
    // Manually specify time format. unix timestamp is example of when this is
    // needed (format='X', see http://momentjs.com/docs/#/parsing/string-format/)
    format: PropTypes.string,

    // ...
    // transfers other properties to rendered <span />
  },

  getDefaultProps: function() {
    return {
      'format': ''
    }
  },

  getInitialState: function() {
    return { raw: false };
  },

  render: function() {
    var { time, format, className, ...others } = this.props;

    if (!time) {
      return <span {...others}></span>;
    }

    var time_text = '';
    var classes = '', title = '';
    if (!this.state.raw) {
      classes += 'timeTextExpandable';
      title = 'Click to view full timestamp';

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
    } else {
      var DATE_RFC2822 = "ddd, DD MMM YYYY HH:mm:ss ZZ";

      time_text = <span>
        <span className="lb">Local:</span>{" "}
          {moment.utc(time, format).local().format(DATE_RFC2822)}<br />
        <span className="lb">UTC:</span>{" "}
          {moment.utc(time, format).format(DATE_RFC2822)}
      </span>;
    }

    var onClick = evt => {
      this.setState({ raw: true });
    };

    classes = classes + " " + (className || "");

    return <span
      onClick={onClick}
      className={classes}
      title={title}
      {...others}>
      {time_text}
    </span>;
  }
});

// given a unix timestamp, renders how long its been since then in hh:mm:ss
// format. Useful to render how long its been since a build started
export var LiveTime = React.createClass({

  propTypes: {
    time: PropTypes.number,
  },

  getInitialState: function() {
    // this is a monotonically increasing number (e.g. timestamps work.)
    // whenever this updates, we rerender our LiveTime text
    return {
      lastUpdated: 0
    };
  },

  render() {
    var now = moment.utc().unix();
    var start = this.props.time;

    var totalSeconds = now - start;
    var seconds = Math.floor(totalSeconds % 60);
    var minutes = Math.floor(totalSeconds / 60);
    if (minutes > 60) {
      var hours = Math.floor(minutes / 60);
      minutes = minutes % 60;
    }

    var text = null; 
    var suffix = ':' + utils.pad(seconds, 2);
    if (hours) {
      text = hours + ':' + utils.pad(minutes, 2) + suffix;
    } else {
      text = minutes + suffix;
    }
    return <span>{text}</span>;
  },

  // timer code

  statics: {
    instances: {},
    refreshTimer: null
  },

  componentDidMount() {
    this.uniqueID = utils.randomID();
    LiveTime.instances[this.uniqueID] = this;

    if (!LiveTime.refreshTimer) {
      LiveTime.refreshTimer = setInterval(arg => {
        _.each(LiveTime.instances, (val, key) => {
          if (!val) { 
            return; 
          }
          if (val.isMounted()) {
            val.setState({
              // this just has to be monotonically increasing, so new Date is fine
              lastUpdated: Date.now()
            });
          }
        });
      // this isn't going to be that smooth :/, but do I really want to change
      // it to something like 250ms?
      }, 1000);
    }
  },

  componentWillUnmount: function() {
    LiveTime.instances[this.uniqueID] = null;
    var timersLeft = _.any(LiveTime.instances, (v, k) => v);

    if (!timersLeft && LiveTime.refreshTimer) {
      // technically I should console.error if refreshTimer is missing
      clearInterval(LiveTime.refreshTimer);
      LiveTime.refreshTimer = null;
    }
  }
});

/*
 * Converts 136 [in seconds] to a string like "2m16s". Note that the backend
 * often returns durations in milliseconds, not seconds!
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

Examples.add('TimeText and display_duration', __ => {
  return [
    <TimeText
      className="block paddingBottomS"
      time={moment.utc().local().toString()}
    />,
    <TimeText className="block" time="September 1, 2008 3:14 PM" />,
    display_duration(57),
    display_duration(3742),
    <span>
      <LiveTime time={moment.utc().unix()} />
      &nbsp;
      <LiveTime time={moment.utc().unix() - 120} />
      &nbsp;
      <LiveTime time={moment.utc().unix() - 3600} />
    </span>
  ];
});
