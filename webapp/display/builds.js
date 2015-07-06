import React from 'react';

import colors from 'es6!utils/colors';
import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

/*
 * Functions and classes for displaying information about builds
 */

// Two classes: StatusDot, StatusMark

/*
 * Renders a square patch based on build state (passed is green,
 * failed is red, unknown is gray, error/weird is brown.) If state
 * is waiting, we render an icon instead.
 */
export var StatusDot = React.createClass({

  propTypes: {
    // big makes it bigger
    size: proptype.oneOf(['normal', 'medium', 'big']),
    // the build state to render (see get_build_state)
    state: proptype.oneOf(all_build_states).isRequired,
    // renders a small number at the lower-right corner                              
    num: proptype.oneOfType(proptype.number, proptype.string)
  },
  
  getDefaultProps: function() {
    return {
      'size': 'normal',
      'num': ''
    }
  },

  render: function() {
    var state = this.props.state, size = this.props.size;

    var dot = null;
    if (state === 'waiting') {
      dot = <i className="fa fa-clock-o" />;
    } else {
      var classes = cx({
        'dotBase': true,
        'mediumDot': size === 'medium',
        'bigDot': size === 'big',
        // NOTE: keep in sync with StatusWithNumber below
        'lt-green-bg': state === "passed",
        // TODO: use darker shade of red for atypical failures
        'lt-red-bg': state === "failed" || state === "nothing",
        'lt-darkestgray-bg': state === "unknown",
      });

      dot = <span className={classes} />;
    }

    var num = null;
    if (this.props.num) {
      // TODO: adjust this so waiting works
      num = <span className="dotText">{this.props.num}</span>;
    }

    return <span className="dotContainer">
      {dot}
      {num}
    </span>;
  }
});

/* 
 * Given a list of builds, render status dots for each in a row (combining
 * adjacent ones with the same result into a single dot w/ number
 */
export var status_dots = function(builds) {
  if (!builds) { return null; }
  var dots_data = [];
  builds.forEach(b => {
    var prev_result = _.last(dots_data) || {name: "none"};
    if (get_build_state(b) === prev_result['name']) {
      prev_result['count'] += 1; 
    } else {
      dots_data.push({name: get_build_state(b), count: 1});
    }
  });
  return _.map(dots_data, d =>
    <StatusDot 
      state={d.name} 
      num={d.count > 1 ? d.count : null} 
    />
  );
}

/*
 * Renders the build status with the build number as inner text
 */
export var StatusWithNumber = React.createClass({
  propTypes: {
    // big makes it bigger
    size: proptype.oneOf(['normal', 'medium', 'big']),
    // the build state to render (see get_build_state)
    state: proptype.oneOf(all_build_states).isRequired,
    // renders a small number at the lower-right corner                              
    text: proptype.string
  },
  
  getDefaultProps: function() {
    return {
      'size': 'normal',
      'text': ''
    }
  },

  render: function() {
    var state = this.props.state, text = this.props.text;

    var classes = cx({
      'statusNumBase': true,
      // NOTE: keep in sync with StatusDot above
      'lt-green-bg': state === "passed",
      // TODO: use darker shade of red for atypical failures
      'lt-red-bg': state === "failed" || state === "nothing",
      'lt-darkestgray-bg': state === "unknown" || state === "waiting",
    });

    var text_markup = null;
    if (this.props.text) {
      switch (this.props.size) {
        case 'normal':
          console.warn("you can't use innerText with normal size...its too small!");
          inner_style = {display: 'none'};
          break;
        case 'medium':
          var inner_style = {
            color: "white",
            padding: 2,
            display: "inline-block"
          };
          break;
        case 'big':
          var inner_style = {
            color: "white",
            display: "inline-block",
            padding: "1px 5px",
            fontSize: 21
          };
      }

      text_markup = <span style={inner_style}>
        {this.props.text}
      </span>;
    }

    return <span className="dotContainer">
      <span className={classes}>
        {text_markup}
      </span>
    </span>;
  }
});

/*
 * Looks at the build's status and result fields to figure out what state the 
 * build is in
 */

var all_build_states = ['passed', 'failed', 'nothing', 'unknown', 'waiting'];

export var get_build_state = function(build) {
  var status = build.status.id, 
    result = build.result.id;

  if (status === 'in_progress' || status === "queued") {
    return 'waiting';
  }

  if (result === 'passed' || result === 'failed') {
    return result;
  } else if (build.result.id === 'aborted' || build.result.id === 'infra_failed') {
    return 'nothing';
  }
  return 'unknown';
}

export var get_build_state_color = function(build) {
  var state = get_build_state(build);
  switch (state) {
    case 'passed':
      return colors.green;
    case 'failed': 
    case 'nothing': 
      return colors.red;
    case 'waiting':
    case 'unknown': 
      return colors.darkGray;
  }
}

export var get_build_cause = function(build) {
  // TODO: This would be a very useful function, but we don't store good
  // metadata about this. This will have to execute some fairly complex
  // logic...
  console.log(build);
  return 'unknown';
}
