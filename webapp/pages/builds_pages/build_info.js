import React, { PropTypes } from 'react';
import moment from 'moment';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesLinks from 'es6!display/changes/links';
import ChangesUI from 'es6!display/changes/ui';
import PostRequest from 'es6!display/post_request';
import SectionHeader from 'es6!display/section_header';
import SimpleTooltip from 'es6!display/simple_tooltip';
import { Button } from 'es6!display/button';
import { Grid, GridRow } from 'es6!display/grid';
import { InfoList, InfoItem } from 'es6!display/info_list';
import { TestDetails } from 'es6!display/changes/test_details';
import { buildSummaryText, manyBuildsSummaryText, get_build_cause, get_cause_sentence, WaitingTooltip } from 'es6!display/changes/build_text';
import { display_duration } from 'es6!display/time';
import { get_runnable_condition, get_runnables_summary_condition, get_runnable_condition_short_text, ConditionDot } from 'es6!display/changes/build_conditions';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

/*
 * An element that shows all the information for a single build
 */

// TODO: store this stuff in the page element so we don't reload on every click
// TODO: don't do that... we want to always get the latest data
// maybe show stale data and update with latest data if possible
export var SingleBuild = React.createClass({

  propTypes: {
    // the build to render
    build: PropTypes.object.isRequired,

    content: PropTypes.oneOf(['short', 'normal'])
  },

  getDefaultProps: function() {
    return {
      content: 'normal'
    };
  },

  getInitialState: function() {
    return {
      // states for toggling inline visibility of test snippets
      expandedTests: {},
      expandedTestsData: {}
    };
  },

  componentDidMount: function() {
    // get richer information about the build
    api.fetch(this, {
      buildDetails : `/api/0/builds/${this.props.build.id}`
    });

    // get info about the phases of each job
    var job_ids = _.map(this.props.build.jobs, j => j.id);

    var endpoint_map = {};
    _.each(job_ids, id => {
      endpoint_map[id] = `/api/0/jobs/${id}/phases?test_counts=1`;
    });

    // TODO: don't refetch every time (cache on parent)
    api.fetchMap(this, 'jobPhases', endpoint_map);
  },

  render: function() {
    var build_prop = this.props.build;

    // get job phases
    var job_ids = _.map(build_prop.jobs, j => j.id);

    var phasesCalls = _.chain(this.state.jobPhases)
      .pick(job_ids)
      .values().value();

    if (!api.allLoaded(phasesCalls)) {
      return <APINotLoaded calls={phasesCalls} />;
    } else if (!api.isLoaded(this.state.buildDetails)) {
      return <APINotLoaded calls={this.state.buildDetails} />;
    }

    var build = this.state.buildDetails.getReturnedData();

    var job_phases = _.mapObject(this.state.jobPhases, (v,k) => {
      return v.getReturnedData();
    });

    // if content = short, we only render the header and failed tests
    var render_all = this.props.content === "normal";

    return <div>
      <div className="marginBottomL">
        {render_all ? this.renderFailedAdvice(build) : null}
        <div className="floatR">
          {render_all ? this.renderButton(build) : null}
        </div>
        {this.renderHeader(build, job_phases)}
        {render_all ? this.renderDetails(build, job_phases) : null}
      </div>
      {this.renderFailedTests(build, job_phases)}
      {render_all ? this.renderJobs(build, job_phases) : null}
    </div>;
  },

  renderHeader: function(build, job_phases) {
    var condition = get_runnable_condition(build);
    var header_subtext = buildSummaryText(build, false, true);
    var colorCls = condition.indexOf('failed') === 0 ?
      'red' : '';

    var dot = <ConditionDot
      condition={condition}
      size="large"
    />;

    var style = {
      verticalAlign: 'top',
      marginLeft: 5
    };

    return <div>
      {dot}
      <div className="inlineBlock" style={style}>
        <div style={{ fontSize: 18 }}>
          <a className="subtle" href={ChangesLinks.projectHref(build.project)}>
            {build.project.name}
          </a>
        </div>
        <div className={colorCls}>
          {header_subtext}
        </div>
      </div>
      <div className="marginTopS">
        {get_cause_sentence(get_build_cause(build))}
      </div>
    </div>;
  },

  renderButton: function(build) {
    return <PostRequest
      parentElem={this}
      name="recreateBuild"
      endpoint={`/api/0/builds/${build.id}/retry/`}>
      <Button type="white">
        <i className="fa fa-repeat marginRightS" />
        Recreate Build
      </Button>
    </PostRequest>;
  },

  renderDetails: function(build, job_phases) {
    var DATE_RFC2822 = "ddd, DD MMM YYYY HH:mm:ss ZZ";

    var attributes = {};
    if (build.dateFinished) {
      attributes['Finished'] = (
        moment.utc(build.dateCreated).local().format(DATE_RFC2822) + 
        ` (${display_duration(build.duration / 1000)})`
      );
    } else if (build.dateStarted) {
      attributes['Started'] = moment.utc(build.dateStarted).local()
        .format(DATE_RFC2822);
    } else {
      attributes['Created'] = moment.utc(build.dateCreated).local()
        .format(DATE_RFC2822);
    }

    var testCount = (!build.stats.test_count && get_runnable_condition(build) === 'waiting') ?
      'In Progress' : build.stats.test_count;

    var testLabel = build.dateFinished ? "Tests Ran" : "Tests Run";
    var buildTestsHref = `/v2/build_tests/${build.id}` +
      (build.testFailures.total > 0 ? '' : "#SlowTests")
    attributes[testLabel] = <span>
      {testCount}{" ("}
      <a href={buildTestsHref}>
        more information
      </a>
      {")"}
    </span>;

    var rows = _.map(attributes, (v,k) => <InfoItem label={k}>{v}</InfoItem>);
    return <div>
      <InfoList className="marginTopM">{rows}</InfoList>
    </div>;
  },

  renderFailedAdvice: function(build) {
    var buildCondition = get_runnable_condition(build);

    if (buildCondition === 'failed_infra') {
      return <div className="messageBox" style={{marginBottom: 15}}>
        There was an infrastructure failure while running this diff.
        You can retry it using the right button on the right.
      </div>;
    } else if (buildCondition === 'failed_aborted') {
      var advice = <div className="messageBox" style={{marginBottom: 15}}>
        This build was aborted. You can retry it using the button on the right.
      </div>;
    }
    return null;
  },

  // which tests caused the build to fail?
  renderFailedTests: function(build, job_phases) {
    if (build.testFailures.total <= 0) {
      return null;
    }

    var rows = [];
    _.each(build.testFailures.tests, test => {
      var href = `/v2/project_test/${test.project.id}/${test.hash}`;

      var onClick = __ => {
        this.setState(
          utils.update_key_in_state_dict('expandedTests',
            test.id,
            !this.state.expandedTests[test.id])
        );
      };

      var expandLabel = !this.state.expandedTests[test.id] ?
        'Expand' : 'Collapse';

      var markup = [
        <div>
          {test.shortName} <a onClick={onClick}>{expandLabel}</a>
          <div className="subText">{test.name}</div>
        </div>
      ];

      rows.push([
        markup,
        <a href={href}>History</a>,
      ]);

      if (this.state.expandedTests[test.id]) {
        rows.push(GridRow.oneItem(<TestDetails testID={test.id} />));
      }
    });

    var more_markup = null;
    if (build.testFailures.total > build.testFailures.tests.length) {
      more_markup = <div className="marginTopS">
        Only showing{" "}
        <span className="lb">{build.testFailures.tests.length}</span>
        {" "}out of{" "}
        <span className="lb">{build.testFailures.total}</span>
        {" "}failed tests.{" "}
        <a href={"/v2/build_tests/"+build.id+"/"}>
        See all
        </a>
      </div>
    }

    var top_spacing = this.props.content === "normal" ?
      'marginTopL paddingTopM' : 'marginTopL';

    return <div className={top_spacing + ' marginBottomL'}>
      <SectionHeader className="noBottomPadding">
        Failed Tests ({build.testFailures.total})
      </SectionHeader>
      <Grid
        colnum={2}
        className="marginBottomM"
        data={rows}
        headers={['Name', 'Links']}
      />
      {more_markup}
    </div>;
  },

  // what did the build actually do?
  renderJobs: function(build, phases) {
    var markup = _.map(build.jobs, (job, index) => {
      // we'll render a table with content from each phase
      return <div className="marginTopM">
        <b>Build Plan:{" " + job.name}</b>
        {this.renderJobTable(job, build, phases)}
      </div>;
    });

    var top_spacing = this.props.content === "normal" ?
      'marginTopL paddingTopM' : 'marginTopL';

    return <div className={top_spacing}>
      <SectionHeader className="noBottomPadding">Breakdown</SectionHeader>
      {markup}
    </div>;
  },

  renderJobTable: function(job, build, all_phases) {
    var failures = _.filter(build.failures, f => f.job_id == job.id);
    var phases = all_phases[job.id];

    // if there's only one row, let's skip rendering the phase name (less
    // visual noise)
    var only_one_row = phases.length === 1 &&
      phases[0].steps && phases[0].steps.length === 1;

    var phases_rows = _.map(phases, phase => {
      return _.map(phase.steps, (jobstep, index) => {
        var jobstepCondition = get_runnable_condition(jobstep);
        var jobstepDot = <ConditionDot condition={jobstepCondition} />;

        var jobstepDuration = null;
        if (jobstepCondition === 'waiting') {
          jobstepDuration = <WaitingTooltip runnable={jobstep} placement="left">
            <span>Running</span>
          </WaitingTooltip>;

          jobstepDot = <WaitingTooltip runnable={jobstep} placement="right">
            <span>{jobstepDot}</span>
          </WaitingTooltip>;
        } else {
          jobstepDuration = jobstep.duration ?
            display_duration(jobstep.duration/1000) : '';
          var label = get_runnable_condition_short_text(jobstepCondition);
          jobstepDot = <SimpleTooltip label={label} placement="right">
            <span>{jobstepDot}</span>
          </SimpleTooltip>;
        }

        var jobstep_failures = _.filter(failures, f => f.step_id == jobstep.id);
        if (jobstep_failures) {
          var innerFailureMarkup = _.map(jobstep_failures, f => {
            var reason = f.reason;
            if (f.id === 'test_failures') {
              // Note: the failure message itself doesn't tell us the correct
              // number of failing tests. I modified the API we use to send the
              // correct number as a separate param
              reason = 'Some tests failed';
              if (jobstep.testFailures && jobstep.testFailures > 0) {
                reason = utils.plural(jobstep.testFailures, 'test(s) failed');
              }
            }

            return <div className="red">{reason}</div>;
          });

          var failureMarkup = <div className="marginTopS">
            {innerFailureMarkup}
          </div>;
        }

        if (!jobstep.node) {
          return [
            index === 0 && !only_one_row ?
              <span className="lb">{phase.name}</span> : "",
            jobstepDot,
            <div>
              <i>Machine not yet assigned</i>
              {failureMarkup}
            </div>,
            '',
            jobstepDuration
          ];
        }

        var nodeLink = jobstep.node.name;

        var logID = jobstep.logSources[0] && jobstep.logSources[0].id;
        if (logID) {
          var logURI = `/v2/job_log/${build.id}/${job.id}/${logID}/`;
          nodeLink = <a href={logURI}>{nodeLink}</a>;
        }
        
        var links = [
          <a className="marginRightM" href={"/v2/node/" + jobstep.node.id}>
            Machine
          </a>
        ];

        if (logID) {
          var raw_log_uri = `/api/0/jobs/${job.id}/logs/${logID}/?raw=1`;
          links.push(
            <a className="external marginRightM" href={raw_log_uri} target="_blank">Raw</a>
          );
        }

        if (jobstep.data.uri) {
          links.push(
            /* skip external class since we'd have two icons */
            <a href={jobstep.data.uri} target="_blank">
              Jenkins{" "}
              {ChangesUI.restrictedIcon()} 
            </a>
          );
        }

        return [
          index === 0 && !only_one_row ?
            <span className="lb">{phase.name}</span> : 
            "",
          jobstepDot,
          <div>{nodeLink}{failureMarkup}</div>,
          links,
          jobstepDuration
        ];
      });
    });

    var job_headers = [
      'Phase',
      'Result',
      'Machine Log',
      'Links',
      'Duration'
    ];

    var cellClasses = [
      'nowrap phaseCell', 'nowrap center', 'wide', 'nowrap', 'nowrap'
    ];

    return <Grid
      colnum={5}
      className="marginTopS"
      data={_.flatten(phases_rows, true)}
      headers={job_headers}
      cellClasses={cellClasses}
    />;
  },
})

export var LatestBuildsSummary = React.createClass({

  propTypes: {
    // All builds for the commit or the latest update to a diff. We'll grab
    // the latest build per project
    builds: PropTypes.object.isRequired,
    // are we rendering for a diff or a commit
    type: PropTypes.oneOf(['diff', 'commit']).isRequired,
    // info about the commit (a changes source object) or diff (from phab.)
    targetData: PropTypes.object,
    // the parent page element.
    pageElem: PropTypes.element,
  },

  render: function() {
    var builds = this.props.builds;
    // TODO: latest builds per project logic is duplicated in sidebar, move to
    // a common helper function

    // we want the most recent build for each project
    var latestByProj = _.chain(builds)
      .groupBy(b => b.project.name)
      .map(proj_builds => _.last(_.sortBy(proj_builds, b => b.dateCreated)))
      .values()
      .value();

    builds = _.map(latestByProj, (b, index) => {
      return <div className="marginTopL paddingTopL fainterBorderTop">
        <SingleBuild build={b} content="short" />
      </div>
    });

    return <div>
      {this.renderHeader(latestByProj)}
      {builds}
    </div>;
  },

  renderHeader: function(latestByProj) {
    var summaryCondition = get_runnables_summary_condition(latestByProj);
    var subtext = manyBuildsSummaryText(latestByProj);
    var colorCls = summaryCondition.indexOf('failed') === 0 ?
      'red' : '';

    var dot = <ConditionDot
      condition={summaryCondition}
      size="large"
      multiIndicator={latestByProj.length > 1}
    />;

    var style = {
      verticalAlign: 'top',
      marginLeft: 5
    };

    return <div>
      {dot}
      <div className="inlineBlock" style={style}>
        <div style={{ fontSize: 18 }}>Latest Builds</div>
        <div className={colorCls}>
          {subtext}
        </div>
      </div>
    </div>;
  },
});

var render_section = function(id, content) {
  var style = {
    padding: 20,
    paddingLeft: 10
  };

  return <div style={style} id={id}>
    {content}
  </div>;
}
