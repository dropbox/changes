import React, { PropTypes } from 'react';
import moment from 'moment';
import { OverlayTrigger, Tooltip } from 'react_bootstrap';

import { LiveTime, display_duration } from 'es6!display/time';
import { get_runnable_condition, get_runnables_summary_condition } from 'es6!display/changes/build_conditions';

import * as utils from 'es6!utils/utils';

/*
 * A bunch of functions that take a build/many builds and renders descriptive
 * text for them. Examples:
 * - 2 out of 1254 tests failed / All tests passed (tests in a build)
 * - 4 out of 7 projects failed (latest builds for a project)
 * - This build was manually started (what caused a build to be kicked off)
 */

/*
 * Summary text for the build. Examples:
 * - 100 tests passed
 * - 3 errors, 2 tests failed (out of 143)
 * - 4 out of 150 tests failed
 */
export var buildSummaryText = function(build, liveTimer = false, showDuration = false) {
  var buildDuration = null;
  if (showDuration && build.duration) {
    buildDuration = display_duration(build.duration / 1000);
  }
  var durationSuffix = format => {
    if (!buildDuration) { return ''; }
    switch (format) {
      case 'parens_after':
        return ` (after ${buildDuration})`;
      case 'parens_in':
        return ` (in ${buildDuration})`;
      case 'plain':
        return ` in ${buildDuration}`;
    }
    return '';
  };

  switch (get_runnable_condition(build)) {
    case 'failed_aborted':
      return 'Aborted' + durationSuffix('parens_after')
    case 'failed_infra':
      return 'Infrastructure failure' + durationSuffix('parens_after');
    case 'passed':
      if (!build.stats.test_count) {
        return 'No tests run' + durationSuffix('parens_in');
      } else {
        return `Ran ${utils.plural(build.stats.test_count, 'test(s)')}`+
          durationSuffix('plain');
      }
    case 'failed':
      var error_count = build.failures ?
        _.filter(build.failures, f => f.id !== 'test_failures').length :
        0; // if its 0, we don't know whether there are 0 failures or if the
           // backend didn't return this info

      var sentence = '';

      if (error_count) {
        sentence += utils.plural(error_count, 'error(s). ');
      } else if (!build.stats.test_failures) {
        // we had a normal failure without errors or test failures. We should
        // call that out.
        sentence += 'No errors. ';
      }

      sentence += build.stats.test_count ?
        `${build.stats.test_failures} of ${build.stats.test_count} tests failed` :
        'No tests run';

      sentence += durationSuffix('parens_after');
      return sentence;
    case 'waiting':
      return liveTimer ? <WaitingLiveText runnable={build} /> : 'Still running';
    case 'unknown':
    default:
      return '';
  }
}

/*
 * Given builds across multiple projects, renders sentences like
 * "4 out of 7 projects failed".
 *
 * We're typically interested in only rendering summary text for the latest
 * build from each project (hence the format of this function)
 *
 * latestPerProject: for the set of relevant projects, the latest build from
 *   each
 */
export var manyBuildsSummaryText = function(latestPerProject) {
  if (!latestPerProject) {
    return 'No projects run';
  }

  var summaryCondition = get_runnables_summary_condition(latestPerProject);
  var hasCondition = _.filter(latestPerProject,
    b => get_runnable_condition(b) === summaryCondition);
  var mixedFailures = _.filter(latestPerProject,
    b => get_runnable_condition(b).indexOf('failed') === 0);
  var hasMixedFailures = mixedFailures.length > 1;

  var plural = hasCondition.length > 1;

  if (summaryCondition === 'passed') {
    return `Ran ${utils.plural(latestPerProject.length, 'project(s)')}`;
  }

  var suffixes = {
    failed_aborted: plural ? 'were aborted' : 'was aborted',
    failed_infra: plural ? 'had infra failures' : 'had an infra failure',
    failed: 'failed',
    waiting: plural ? 'are still running' : 'is still running',
    unknown: plural ? 'have an unknown status' : 'has an unknown status',
  };

  var suffix = suffixes[summaryCondition];
  if (!suffix) {
    console.log(`unknown condition ${summaryCondition}!`);
    return '';
  }

  if (hasMixedFailures) {
    suffix += ` (${mixedFailures.length} total failures)`
  }

  return `${hasCondition.length} out of ${utils.plural(latestPerProject.length, 'project(s)')} ${suffix}`;
}

// Text related to the cause of a build

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
    'buildpoker': 'buildpoker',
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

/* Live-updating timers */

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
export var WaitingLiveText = React.createClass({

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
