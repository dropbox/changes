import React, { PropTypes } from 'react';
import moment from 'moment';
import { Popover, OverlayTrigger, Tooltip } from 'react_bootstrap';

import ChangesLinks from 'es6!display/changes/links';
import { Error, ProgrammingError } from 'es6!display/errors';
import { LiveTime } from 'es6!display/time';
import { buildSummaryText } from 'es6!display/changes/build_text';
import { get_runnable_condition, get_runnables_summary_condition, get_runnable_condition_color_cls, ConditionDot } from 'es6!display/changes/build_conditions';

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
    var builds_for_last_code_change = buildsForLastCodeChange(builds);

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
      var subtext = buildSummaryText(b, true);

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

    var subtext = buildSummaryText(build, true);

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
// have the builds for the latest update. Its safe to run this on non-diffs...we'll
// just return the original list
//
// we won't know about the latest update if no builds have run for it (instead
// returning builds for the second-latest update), but I think that's fine
export var buildsForLastCodeChange = function(builds) {
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
