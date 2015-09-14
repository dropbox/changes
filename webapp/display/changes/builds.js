import React, { PropTypes } from 'react';
import { Popover, OverlayTrigger, Tooltip } from 'react_bootstrap';

import ChangesLinks from 'es6!display/changes/links';
import { Error, ProgrammingError } from 'es6!display/errors';

import * as api from 'es6!server/api';

var cx = React.addons.classSet;

/*
 * Shows the status of many builds run for a single code change (e.g. a commit
 * or diff.) Despite the name, this widget can also handle showing a single
 * build...you use this for any interface where you might be showing builds
 * from more than one project.
 */
export var ManyBuildsStatus = React.createClass({

  propTypes: {
    builds: PropTypes.array,
  },

  render: function() {
    var builds = this.props.builds;

    if (!builds) {
      // TODO: we could render an empty widget that went to the empty build page
      return <div />;
    }

    // If this is a diff, we only want to look at builds that ran on the last
    // code change
    var builds_for_last_code_change = get_builds_for_last_change(builds);

    // grab the latest builds for each project
    var builds_by_project = _.groupBy(builds_for_last_code_change,
      b => b.project.slug);
    var latest_builds = _.map(builds_by_project, builds => {
      return _.chain(builds)
        .sortBy(b => b.dateCreated)
        .last()
        .value();
    });

    // TOOD: how to order projects? Right now, I do it alphabetically by project name...
    // I think that makes this easiest to instantly parse every time someone views this.
    latest_builds = _.sortBy(latest_builds, b => b.project.name);

    var tooltip_markup = _.map(latest_builds, b => {
      var subtext = '';
      if (b.stats.test_count === 0) {
        subtext = 'No tests run';
      } else if (b.stats.test_failures > 0) {
        subtext = `${b.stats.test_failures} of ${b.stats.test_count} tests failed`;
      } else {
        subtext = `All ${b.stats.test_count} tests passed`;
      }

      return <div style={{textAlign: "left"}}>
        <div style={{ display: "inline-block", paddingTop: 10, paddingRight: 5}}>
          <ConditionDot condition={get_runnable_condition(b)} />
        </div>
        <div style={{ verticalAlign: "top", display: "inline-block"}}>
          <div>{b.project.name}</div>
          <span className="mediumGray">{subtext}</span>
        </div>
      </div>
    });

    var tooltip = <Tooltip>{tooltip_markup}</Tooltip>;

    var summary_condition = get_runnables_summary_condition(latest_builds);

    var glow = latest_builds.length > 1;

    var builds_href = ChangesLinks.buildsHref(latest_builds);

    return <OverlayTrigger
      placement="right"
      overlay={tooltip}>
      <a className="buildStatus" href={builds_href}>
        <ConditionDot condition={summary_condition} glow={glow} />
      </a>
    </OverlayTrigger>;
  }
});

/*
 * Shows the status of a single build. This tooltip can go into more details
 * than ManyBuildsStatus
 */
export var SingleBuildStatus = React.createClass({

  render: function() {
    var build = this.props.build;
    var condition = get_runnable_condition(build);

    var num = null;
    if (build.stats && build.stats.test_failures) {
      num = build.stats.test_failures;
    }
    var dot = <ConditionDot condition={condition} num={num} />;

    var href = ChangesLinks.buildHref(build);

    /*
    // TODO: show popover for any failure, not just test failures
    if (build.stats['test_failures'] > 0) {

      var popover = this.getFailedTestsPopover();
      if (popover) {
        return <div>
          <OverlayTrigger
            placement='right'
            overlay={popover}>
            <div>{build_widget}</div>
          </OverlayTrigger>
        </div>;
      }
    }
    */

    // TODO: more than this
    var tooltip = <Tooltip>TODO</Tooltip>;
    return <OverlayTrigger
      placement="right"
      overlay={tooltip}>
      <a className="buildStatus" href={href}>
        {dot}
      </a>
    </OverlayTrigger>;
  },

  getFailedTestsPopover: function() {
    var elem = this.props.parentElem, build = this.props.build;

    var state_key = "_build_widget_failed_tests";

    // make sure parentElem has a state object
    // TODO: we could silently add this ourselves if missing
    if (!elem.state && elem.state !== {}) {
      return <Popover> <ProgrammingError>
        Programming Error: The parentElem of BuildWidget must implement
        getInitialState()! Just return{" {}"}
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

// if a list of builds is for a differential diff, filter them so that we only
// have the builds for the latest update
//
// there's a slight bug where we won't know about the latest update if no
// builds have run for it, but I think this is fine as-is
var get_builds_for_last_change = function(builds) {
  var revision_ids = [];
  var diff_ids = [];

  // we only do something if every build is from the same phabricator revision
  // id
  _.each(builds, build => {
    var build_revision_id = build.source.patch &&
      build.source.data['phabricator.revisionID'];

    // must be from a phabricator revision
    if (!build_revision_id) { return builds; }

    revision_ids.push(build.source.data['phabricator.revisionID']);
    diff_ids.push(build.source.data['phabricator.diffID']);
  });

  revision_ids = _.uniq(revision_ids);
  diff_ids = _.uniq(diff_ids).sort().reverse();

  if (revision_ids.length > 1) {
    return builds;
  }

  var latest_diff_id = diff_ids[0];
  return _.filter(builds,
    b => b.source.data['phabricator.diffID'] === latest_diff_id);
}


/*
 * General classes/functions for all runnables (objects with a status and a
 * result.) Can use these for jobs, jobsteps, etc.
 */

/*
 * Renders a rounded square with a color that indicates the condition of the
 * runnable (passed/failed/unknown/not yet run.) Shows a clock icon instead of
 * the dot if the build hasn't finished yet.
 */
export var ConditionDot = React.createClass({

  propTypes: {
    // the runnable condition to render (see get_runnable_condition)
    condition: PropTypes.oneOf(all_build_conditions).isRequired,
    // renders a small number at the lower-right corner
    num: PropTypes.oneOfType(PropTypes.number, PropTypes.string),
    // smaller = 12px, small = 16px
    size: PropTypes.oneOf(["smaller", "small", "medium", "large"]),
    // a glow is a ui indicator that this dot shows results from multiple items
    glow: PropTypes.bool
  },

  getDefaultProps: function() {
    return {
      num: '',
      size: 'small',
      glow: false
    }
  },

  render: function() {
    var condition = this.props.condition;

    var dot = null;
    if (condition === 'waiting') {
      var font_sizes = {
        smaller: 12,
        small: 16,
        medium: 26,
        large: 45
      };

      dot = <i
        className="fa fa-clock-o conditionDotIcon"
        style={{ fontSize: font_sizes[this.props.size], color: "#007ee5" }}
      />;
    } else {
      var classes = [
        'conditionDot',
        this.props.size,
        get_runnable_condition_color_cls(condition, true),
        this.props.glow ? 'glow' : ''
      ];

      dot = <span className={classes.join(" ")} />;
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

var all_build_conditions = ['passed', 'failed', 'failed_unusual', 'unknown', 'waiting'];

/*
 * Looks at a build/job/jobstep's status and result fields to figure out what
 * condition the build is in. For the most part I treat failed and failed_unusual
 * the same...someone with a better understanding of changes can differentiate
 * these if they want
 */
export var get_runnable_condition = function(runnable) {
  var status = runnable.status.id, result = runnable.result.id;

  if (status === 'in_progress' || status === "queued") {
    return 'waiting';
  }

  if (result === 'passed' || result === 'failed') {
    return result;
  } else if (result === 'aborted' || result === 'infra_failed') {
    return 'failed_unusual';
  }
  return 'unknown';
}

/*
 * Combines the conditions of a bunch of runnables into a single summary
 * condition: if any failed or haven't finished, returns failed/waiting, etc.
 *
 * NOTE: treats failed_unusual as failed
 */
export var get_runnables_summary_condition = function(runnables) {
  var any_failed = _.any(runnables,
    r => get_runnable_condition(r).indexOf('failed') === 0);

  var any_waiting = _.any(runnables,
    r => get_runnable_condition(r) === 'waiting');

  var any_unknown = _.any(runnables,
    r => get_runnable_condition(r) === 'unknown');

  return (any_failed && 'failed') ||
    (any_waiting && 'waiting') ||
    (any_unknown && 'unknown') ||
    'passed';
}

var get_runnable_condition_color_cls = function(condition, background = false) {
  switch (condition) {
    case 'passed':
      return background ? 'greenBg' : 'green';
    case 'failed':
    case 'failed_unusual':
      return background ? 'redBg' : 'red';
    case 'waiting':
      return background ? 'bluishGrayBg' : 'bluishGray';
    case 'unknown':
      return background ? 'mediumGrayBg' : 'mediumGray';
  }
}

/*
 * What caused the build to be kicked off? We can usually tell from the tags
 * attribute, but we sometimes need to look at the almost always useless cause
 * attribute.
 */
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
