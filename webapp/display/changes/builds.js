import React, { PropTypes } from 'react';
import moment from 'moment';
import { Popover, OverlayTrigger, Tooltip } from 'react_bootstrap';

import ChangesLinks from 'es6!display/changes/links';
import Examples from 'es6!display/examples';
import { Error, ProgrammingError } from 'es6!display/errors';
import { LiveTime } from 'es6!display/time';

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
      if (get_runnable_condition(b) === 'waiting') {
        subtext = <WaitingLiveText runnable={b} />;
      } else if (!b.stats.test_count) {
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
 * How long has it been since a runnable started?
 */
export var WaitingTooltip = React.createClass({

  render() {
    var tooltip = <Tooltip>
      <WaitingLiveText runnable={this.props.runnable} />
    </Tooltip>;

    return <OverlayTrigger
      placement={this.props.placement}
      overlay={tooltip}>
      {this.props.children}
    </OverlayTrigger>;
  }

});

// internal component that implements the above
var WaitingLiveText = React.createClass({

  render() {
    var runnable = this.props.runnable;

    if (!runnable.dateStarted) {
      return <span>Not yet started</span>;
    }

    var unix = moment.utc(runnable.dateStarted).unix();

    return <span>
      Time Since Start:{" "}
      <LiveTime time={unix} />
    </span>;
  }
})

/*
 * Shows the status of a single build. This tooltip can go into more details
 * than ManyBuildsStatus (showing the names of the failing tests)
 */
export var SingleBuildStatus = React.createClass({

  MAX_TESTS_IN_TOOLTIP: 15,

  propTypes: {
    build: PropTypes.object,
    placement: PropTypes.string,
    parentElem: PropTypes.element
  },

  render: function() {
    var build = this.props.build;
    var condition = get_runnable_condition(build);
    var dot = <ConditionDot condition={condition} />;
    var href = ChangesLinks.buildHref(build);

    var extra_text = null;

    // TODO: show popover for any failure, not just test failures
    var tooltip = this.getStandardTooltip();
    if (build.stats['test_failures'] > 0) {
      tooltip = this.getFailedTestsTooltip();
      extra_text = build.stats['test_failures'];
    }

    var extra_text_classes = "buildWidgetText " +
      get_runnable_condition_color_cls(condition)

    var widget = <a className="buildStatus" href={href}>
      {dot}
      <span className={extra_text_classes}>
        {extra_text}
      </span>
    </a>;

    if (tooltip) {
      return <div>
        <OverlayTrigger
          placement={this.props.placement || "right"}
          overlay={tooltip}>
          <div>{widget}</div>
        </OverlayTrigger>
      </div>;
    }

    return widget;
  },

  getStandardTooltip() {
    return <Tooltip>{this.getTooltipHeader()}</Tooltip>;
  },

  getTooltipHeader() {
    var build = this.props.build;

    var subtext = '';
    if (get_runnable_condition(build) === 'waiting') {
      subtext = <WaitingLiveText runnable={build} />;
    } else if (!build.stats.test_count) {
      subtext = 'No tests run';
    } else if (build.stats.test_failures > 0) {
      subtext = `${build.stats.test_failures} of ${build.stats.test_count} tests failed`;
    } else {
      subtext = `All ${build.stats.test_count} tests passed`;
    }

    return <div style={{textAlign: "left"}}>
      <div style={{ display: "inline-block", paddingTop: 10, paddingRight: 5}}>
        <ConditionDot condition={get_runnable_condition(build)} />
      </div>
      <div style={{ verticalAlign: "top", display: "inline-block"}}>
        <div>{build.project.name}</div>
        <span className="mediumGray">{subtext}</span>
      </div>
    </div>;
  },

  getFailedTestsTooltip: function() {
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
      var tests = data.testFailures.tests.slice(0, this.MAX_TESTS_IN_TOOLTIP);
      var list = _.map(tests, t => {
        return <div>{t.shortName}</div>;
      });

      if (tests.length < build.stats['test_failures']) {
        list.push(
          <div className="marginTopS"> <em>
            Showing{" "}
            {tests.length}
            {" "}out of{" "}
            {build.stats['test_failures']}
            {" "}test failures
          </em> </div>
        );
      }

      return <Tooltip key={+new Date()}>
        {this.getTooltipHeader()}
        <div style={{textAlign: "left", marginTop: 10, marginLeft: 25}}>
          <span className="bb">Failed Tests:</span>
          {list}
        </div>
      </Tooltip>;
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

      return <Tooltip>
        {this.getTooltipHeader()}
        {data_fetcher}
        <div style={{textAlign: "left", marginTop: 10, marginLeft: 25}}>
          Loading failed test list
        </div>
      </Tooltip>;
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
 * runnable (passed/failed/unknown/not yet run.) Shows icons instead of
 * dots for builds that haven't finished yet or were cancelled
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
    if (condition === 'waiting' || condition === 'failed_aborted') {
      var font_sizes = {
        smaller: 12,
        small: 16,
        medium: 26,
        large: 45
      };
      var style = {
        fontSize: font_sizes[this.props.size], 
      };
      if (this.props.size === 'medium') {
        style = _.extend(style, {marginLeft: 2, marginRight: 6});
      }

      var classes = {
        common: 'fa conditionDotIcon ',
        waiting: "fa-clock-o blue",  // blue instead of blue-gray
        'failed_aborted': 'red fa-ban'
      }
      var className = classes['common'] + classes[condition];

      dot = <i
        className={className}
        style={style}
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

var all_build_conditions = ['passed', 'failed', 'failed_infra', 'failed_aborted', 'unknown', 'waiting'];

/*
 * Looks at a build/job/jobstep's status and result fields to figure out what
 * condition the build is in. There are a bunch of failure conditions with a
 * common prefix, so you can just check failure with indexOf('failed') === 0.
 */
export var get_runnable_condition = function(runnable) {
  var status = runnable.status.id, result = runnable.result.id;

  if (status === 'in_progress' || status === "queued") {
    return 'waiting';
  }

  if (result === 'passed' || result === 'failed') {
    return result;
  } else if (result === 'aborted') {
    return 'failed_aborted';
  } else if (result === 'infra_failed') {
    return 'failed_infra';
  }
  return 'unknown';
}

/*
 * Combines the conditions of a bunch of runnables into a single summary
 * condition: if any failed or haven't finished, returns failed/waiting, etc.
 */
export var get_runnables_summary_condition = function(runnables) {
  var any_condition = condition => _.any(runnables,
    r => get_runnable_condition(r) === condition);

  var any_aborted = any_condition('failed_aborted');
  var any_failed_infra = any_condition('failed_infra');
  var any_failed = any_condition('failed');
  var any_waiting = any_condition('waiting');
  var any_unknown = any_condition('unknown');

  return (any_aborted && 'failed_aborted') ||
    (any_failed_infra && 'failed_infra') ||
    (any_failed && 'failed') ||
    (any_waiting && 'waiting') ||
    (any_unknown && 'unknown') ||
    'passed';
}

// short, readable text for runnable conditions
export var get_runnable_condition_short_text = function(condition) {
  var names = {
    passed: 'passed',
    failed: 'failed',
    'failed_aborted': 'aborted',
    'failed_infra': 'infrastructure failure',
    waiting: 'in progress',
  };
  return names[condition] || 'unknown';
}

export var get_runnable_condition_color_cls = function(condition, background = false) {
  switch (condition) {
    case 'passed':
      return background ? 'greenBg' : 'green';
    case 'failed':
    case 'failed_aborted':
      return background ? 'redBg' : 'red';
    case 'failed_infra':
      return background ? 'blackBg' : 'black';
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
  if (build.cause.id === 'retry') {
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

/*
 * Renders a sentence describing how this build was created
 */
export var get_cause_sentence = function(cause) {
  switch (cause) {
    case 'manual':
      // If I start a build with someone else's commit, they're still listed as
      // the build author. So there's no way to be more specific than someone
      return 'This build was manually started by someone';
    case 'arc test': 
      return 'This build was started via arc test';
    case 'commit': 
      return 'This build was automatically started after commit';
    case 'phabricator': 
      return 'This build was started by our phabricator-changes integration';
    default:
      return 'The trigger for this build was ' + cause;
  }
}

Examples.add('ConditionDot', __ => {
  return [
    <ConditionDot condition="passed" />,
    <ConditionDot condition="waiting" />,
    <ConditionDot condition="failed" />,
    <ConditionDot condition="failed_infra" />,
    <ConditionDot condition="failed_aborted" />,
    <ConditionDot condition="unknown" />,
    <ConditionDot condition="passed" num={2} />,
    <ConditionDot condition="passed" glow={true} />,
    <div>
      <ConditionDot className="marginRightS" condition="failed" size="small" />
      <ConditionDot className="marginRightS" condition="failed" size="smaller" />
      <ConditionDot className="marginRightS" condition="failed" size="medium" />
      <ConditionDot className="marginRightS" condition="failed" size="large" />
    </div>
  ];
});
