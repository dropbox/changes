import React from 'react';

import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

// Two classes: StatusDot, StatusMark

/*
 * Renders a square patch based on build status (passed is green,
 * failed is red, unknown is gray, error/weird is brown.)
 */
export var StatusDot = React.createClass({

  propTypes: {
    // big makes it bigger
    size: proptype.oneOf(['normal', 'big']),
    // the build result to render. Weird is an extra state the frontend can use
    result: proptype.oneOf(['unknown', 'passed', 'failed', 
                            'skipped', 'aborted', 'infra_failed',
                            'weird']).isRequired,
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
    var result = this.props.result;

    var classes = cx({
      'dotBase': true,
      'bigDot': this.props.size === 'big',
      'lt-green-bg': result === "passed",
      'lt-red-bg': result === "failed",
      'lt-darkestgray-bg': result === "unknown",
      'lt-brown-bg': result === 'error' || result === 'weird'
    });

    var num = null;
    if (this.props.num) {
      num = <span className="dotText">{this.props.num}</span>;
    }

    return <span className="dotContainer">
      <span className={classes} />
      {num}
    </span>;
  }
});

/* 
 * Given a list of builds, render status dots for each (combining
 * adjacent ones with the same result into a single dot w/ number
 */
export var status_dots = function(builds) {
  if (!builds) { return null; }
  var dots_data = [];
  builds.forEach(b => {
    var prev_result = _.last(dots_data) || {name: "none"};
    if (b.result.id === prev_result['name']) {
      prev_result['count'] += 1; 
    } else {
      dots_data.push({name: b.result.id, count: 1});
    }
  });
  return _.map(dots_data, d =>
    <StatusDot 
      result={d.name} 
      num={d.count > 1 ? d.count : null} 
    />
  );
}

/*
 * Renders a symbol from fontawesome based on build status.
 * Still uses color-coding
 * TODO: not finished
 */
export var StatusMark = React.createClass({
  getDefaultProps: function() {
    return {
      'size': 'normal',
      'result': 'unknown',
      'num': ''
    }
  },

  render: function() {
    /*
     * a list of all the icons that might be appropriate. Made a list of them 
     * here to make it easy to experiment.
     *  passed_icons = ["fa-check", "fa-check-circle", "fa-check-square", 
     *    "fa-check-square-o"];
     *
     * TODO: add waiting as a semantic possibility for builds. How is it
     * different than unknown?
     *
     *  unknown_icons = ["fa-cog", "fa-spinner", "fa-clock-o", "fa-cogs"];
     *  failed_icons = ["fa-times", "fa-ban", "fa-minus-square"];
     *  weird_icons = ["fa-exclamation-triangle", "fa-exclamation-circle", 
     *   "fa-asterisk", "fa-exclamation", "fa-bomb", "fa-bug"];
     */

    var result = this.props.result;

    utils.assert_is_one_of(this.props.size,
      ['normal', 'big']);

    utils.assert_is_one_of(result,
      ['passed', 'failed', 'unknown', 'error', 'weird']);

    var classes = cx({
      'fa': true,
      'fa-check-circle': result === "passed",
      'lt-green': result === "passed",
      'fa-times': result === "failed",
      'fa-clock-o': result === "unknown",
      'fa-bomb': result === 'error' || result === 'weird'
    });

    var num = null;
    if (this.props.num) {
      num = <span className="dotText">{this.props.num}</span>;
    }

    return <span className="dotContainer">
      <i className={classes} />
      {num}
    </span>;
  }
});
