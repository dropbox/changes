import React from 'react';
import { Popover, OverlayTrigger } from 'react_bootstrap';

import { ProgrammingError } from 'es6!display/errors';
import { display_duration_pieces } from 'es6!display/time';

import * as api from 'es6!server/api';

import colors from 'es6!utils/colors';

var cx = React.addons.classSet;

/*
 * Functions and classes for displaying information about builds. A bunch of
 * these functions work on "runnables": e.g. builds, jobs, or jobsteps (objects
 * with a status and result)
 */

// Show information about the latest build to a commit-in-project
export var BuildWidget = React.createClass({

  propTypes: {
    // the build to render the widget for
    build: React.PropTypes.object.isRequired,
    // we display a list of failed tests on hover. To do that, we need to fetch
    // ajax data, which we store in parentElem's state
    parentElem: React.PropTypes.element
  },

  render: function() {
    var build = this.props.build;
    var build_state = get_runnable_state(build);

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

    var href = null;
    if (build.source.patch && build.source.data['phabricator.revisionID']) {
      href = URI(`/v2/diff/D${build.source.data['phabricator.revisionID']}`)
        .search({ buildID: build.id })
        .toString();
    } else if (!build.source.patch) {
      href = URI(`/v2/commit/${build.source.id}/`)
        .search({ buildID: build.id })
        .toString();
    } else {
      // TODO
      href = '';
    }

    // return the widget, possibly showing failed tests on hover
    var build_widget = <a href={href} className="buildWidget">
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

    // TODO: show popover for any failure, not just test failures
    if (build.stats['test_failures'] > 0) {

      var popover = this.getFailedTestsPopover();
      if (popover) {
        return <div>
          <OverlayTrigger
            trigger={['hover', 'focus']}
            placement='right'
            overlay={popover}>
            <div>{build_widget}</div>
          </OverlayTrigger>
        </div>;
      }
    }

    return build_widget;
  },

  getFailedTestsPopover: function() {
    var elem = this.props.parentElem, build = this.props.build;

    var state_key = "_build_widget_failed_tests";

    // make sure parentElem has a state object
    // TODO: we could silently add this ourselves if missing
    if (!elem.state && elem.state !== {}) {
      return <Popover> <ProgrammingError>
        Programming Error: The parentElem of BuildWidget must implement
        getInitialState()! Just return {" {}"}
      </ProgrammingError> </Popover>;
    }

    if (elem.state[state_key] &&
        api.isLoaded(elem.state[state_key][build.id])) {
      var data = elem.state[state_key][build.id].getReturnedData();
      var list = _.map(data.testFailures.tests, t => {
        return <div>{_.last(t.name.split("."))}</div>;
      });

      if (data.testFailures.tests.length < build.stats['test_failures']) {
        list.push(
          <div className="marginTopS"> <em>
            Showing{" "}
            {data.testFailures.tests.length}
            {" "}out of{" "}
            {build.stats['test_failures']}
            {" "}test failures
          </em> </div>
        );
      }

      return <Popover>
        <span className="bb">Failed Tests:</span>
        {list}
      </Popover>;
    } else {
      // we want to fetch more build information and show a list of failed
      // tests on hover. To do this, we'll create an anonymous react element
      // that does data fetching on mount
      var data_fetcher_defn = React.createClass({
        componentDidMount() {
          if (!elem.state[state_key] ||
              !elem.state[state_key][build.id]) {
            api.fetchMap(elem, state_key, {
              [ build.id ]: `/api/0/builds/${build.id}/`
            });
          }
        },

        render() {
          return <span />;
        }
      });

      var data_fetcher = React.createElement(
        data_fetcher_defn,
        {elem: elem, buildID: build.id}
      );

      return <Popover>
        {data_fetcher}
        Loading failed test list
      </Popover>;
    }
  },

});

/*
 * Renders a square patch based on runnable state (passed is green,
 * failed is red, unknown is gray.) If state is waiting, we render 
 * an icon instead.
 */
export var StatusDot = React.createClass({

  propTypes: {
    // the runnable state to render (see get_runnable_state)
    state: React.PropTypes.oneOf(all_build_states).isRequired,
    // renders a small number at the lower-right corner
    num: React.PropTypes.oneOfType(React.PropTypes.number, React.PropTypes.string)
  },

  getDefaultProps: function() {
    return {
      'num': ''
    }
  },

  render: function() {
    var state = this.props.state;

    var dot = null;
    if (state === 'waiting') {
      dot = <i className="fa fa-clock-o" />;
    } else {
      var classes = cx({
        'dotBase': true,
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
      {dot}{num}
    </span>;
  }
});

/*
 * Show a list of icons for the latest builds to a diff
 * TODO: unify this with BuildWidget
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
    .map(get_runnable_state)
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
    if (get_runnable_state(b) === prev_result['name']) {
      prev_result['count'] += 1;
    } else {
      dots_data.push({name: get_runnable_state(b), count: 1});
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
 * Looks at the build's status and result fields to figure out what state the
 * build is in. For the most part I treat failed and nothing the same...someone
 * with a better understanding of changes can differentiate these if they want
 */

var all_build_states = ['passed', 'failed', 'nothing', 'unknown', 'waiting'];

// builds, jobsteps, etc.
export var get_runnable_state = function(runnable) {
  var status = runnable.status.id, result = runnable.result.id;

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
      return colors.darkGray;
    case 'unknown':
      return colors.black;
  }
}

export var get_build_cause = function(build) {
  var tags = build.tags;
  if (build.cause === 'retry') {
    // manually triggered retry (either from phabricator or the changes ui)
    return 'manual';
  }

  var causes_from_tags = {
    // user ran build using arc test
    'arc test': 'arc test',
    // standard build that got kicked off due to a new commit
    'commit': 'commit',
    // build for a diff that was created/updated in phabricator
    'phabricator': 'phabricator',
    // this is a very temporary hack inside of dropbox. Talk to dev-tools about
    // it
    'buildpoker': 'commit (hack)',
    // build by the commit queue infrastructure
    'commit-queue': 'commit queue',
  }

  var cause = 'unknown';
  _.each(causes_from_tags, (v, k) => {
    if (_.contains(tags, k)) {
      cause = v;
    }
  });
  return cause;
}
