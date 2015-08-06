import React from 'react';

import { ProgrammingError } from 'es6!display/errors';
import { display_duration_pieces } from 'es6!display/time';

import colors from 'es6!utils/colors';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

/*
 * Functions and classes for displaying information about builds
 */

// Show information about the latest build to a commit-in-project
export var BuildWidget = React.createClass({

  propTypes: {
    build: proptype.object.isRequired,
    // override default href. TODO: something better
    href: proptype.string,
  },

  render: function() {
    var build = this.props.build;
    var build_state = get_build_state(build);

    var dot = <StatusDot state={build_state} />;

    var content = null;
    switch (build_state) {
      case 'passed':
      case 'failed':
      case 'nothing':
        var day_hour_style = {
          fontWeight: 900
        };
        if (!build.duration) {
          content = '---';
        } else {
          var duration = display_duration_pieces(build.duration / 1000)
          content = [
            <span style={day_hour_style}>{duration.slice(0, 2)}</span>,
            duration.slice(2)
          ];
        }
        break;
      case 'unknown':
        content = "?";
        break;
      case 'waiting':
        var style = _.extend({}, content_style, { verticalAlign: 'middle', marginLeft: 5});
        // I thought about rendering a timer about how long the build has been
        // running, but if it keeps increasing, people will expect this to
        // be live / update once the build is done
        content = <span style={{verticalAlign: "middle", paddingLeft: 2}}>Running</span>;
    }

    var test_failures = null;
    if (build.stats['test_failures'] > 0) {
      var failure_style = {
        color: '#ee2e24',
        display: 'inline-block',
        fontSize: 'smaller',
        fontWeight: 'bold',
        marginLeft: 3,
        marginBottom: 1
      };

      //<div style={{position: 'absolute', right: 0, top: 2, fontSize: 'smaller', fontWeight: 'bold', color: '#ee2e24'}}>
      test_failures =
        <div style={failure_style}>
          {build.stats['test_failures']}
          <i className="fa fa-times-circle-o"></i>
        </div>;
    }

    var content_style = {
      color: '#777',
      display: 'inline-block',
      fontSize: 'smaller',
      fontWeight: 'bold',
      verticalAlign: 'top'
    };

    var href = this.props.href;
    if (!href) {
      var href = '/v2/project_commit/' +
        build.project.slug + '/' +
        build.source.id;
    }
    return <a href={href} className="buildWidget">
      <div style={{verticalAlign: 'middle', display: 'inline-block'}}>
        {dot}
      </div>
      <div style={{verticalAlign: 'middle', display: 'inline-block'}}>
        <div style={content_style}>
          {content}
          {test_failures}
        </div>
      </div>
    </a>;
  }
});

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
 * Show a list of icons for the latest builds to a diff
 */
export var status_dots_for_diff = function(builds) {
  var builds_by_diff_id = {};
  _.each(builds, b => {
    var diff_update_id = b.source.data['phabricator.diffID'];
    builds_by_diff_id[diff_update_id] = builds_by_diff_id[diff_update_id] || [];
    builds_by_diff_id[diff_update_id].push(b);
  });
  var latest_diff_id = _.chain(builds_by_diff_id).keys().max().value();

  var states = _.chain(builds_by_diff_id[latest_diff_id])
    .map(get_build_state)
    .countBy()
    .value();

  // treat nothing and failed the same
  states['failed'] = (states['failed'] || 0) + (states['nothing'] || 0);
  delete states['nothing'];

  var dots = _.chain(states)
    .pick(v => v > 0)
    .mapObject((v,k) => <StatusDot state={k} num={v > 1 ? v : null} />)
    .value();

  if (all_build_states.length != 5) { // I'm paranoid
    return <ProgrammingError>
      You need to update the return value of the status_dots_for_diff function
    </ProgrammingError>;
  }

  // we want to return the statuses in a specific order
  return _.compact([dots['waiting'], dots['failed'], dots['passed'], dots['unknown']]);
}

/*
 * Given a list of builds, render status dots for each in an ordered row
 * (combining adjacent ones with the same result into a single dot w/ number
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
 * build is in. For the most part I treat failed and nothing the same...someone
 * with a better understanding of changes can differentiate these if they want
 */

var all_build_states = ['passed', 'failed', 'nothing', 'unknown', 'waiting'];

export var get_build_state = function(build) {
  return get_runnable_state(build.status.id, build.result.id);
}

// builds, jobsteps, etc.
export var get_runnable_state = function(status, result) {
  if (status === 'in_progress' || status === "queued") {
    return 'waiting';
  }

  if (result === 'passed' || result === 'failed') {
    return result;
  } else if (result === 'aborted' || result === 'infra_failed') {
    return 'nothing';
  }
  return 'unknown';
}

export var get_state_color = function(state) {
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
  var tags = build.tags;
  if (build.cause === 'retry') {
    // manually triggered retry (either from phabricator or the changes ui)
    return 'manual';
  }

  if (_.contains(tags, 'arc test')) {
    // user ran build using arc test
    return 'arc test';
  }

  if (_.contains(tags, 'commit')) {
    // standard build that got kicked off due to a new commit
    return 'commit';
  }

  if (_.contains(tags, 'phabricator')) {
    // build for a diff that was created/updated in phabricator
    return 'phabricator';
  }

  if (_.contains(tags, 'buildpoker')) {
    // this is a very temporary hack inside of dropbox. Talk to dev-tools about
    // it
    return 'commit (hack)';
  }

  if (_.contains(tags, 'commit-queue')) {
    // build by the commit queue infrastructure
    return 'commit queue';
  }

  return 'unknown';
}
