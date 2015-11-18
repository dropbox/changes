import React, { PropTypes } from 'react';
import moment from 'moment';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesLinks from 'es6!display/changes/links';
import ChangesUI from 'es6!display/changes/ui';
import Request from 'es6!display/request';
import SectionHeader from 'es6!display/section_header';
import SimpleTooltip from 'es6!display/simple_tooltip';
import { Button } from 'es6!display/button';
import { Grid, GridRow } from 'es6!display/grid';
import { InfoList, InfoItem } from 'es6!display/info_list';
import { JobstepDetails } from 'es6!display/changes/jobstep_details';
import { TestDetails } from 'es6!display/changes/test_details';
import { buildSummaryText, manyBuildsSummaryText, get_build_cause, get_cause_sentence, WaitingTooltip } from 'es6!display/changes/build_text';
import { display_duration, formatTime } from 'es6!display/time';
import { get_runnable_condition, get_runnables_summary_condition, get_runnable_condition_short_text, ConditionDot } from 'es6!display/changes/build_conditions';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

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
      expandedJobSteps: {},
      expandedJobStepTimelines: {},
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
          {render_all ? this.renderButtons(build) : null}
        </div>
        {this.renderHeader(build, job_phases)}
        {render_all ? this.renderDetails(build, job_phases) : null}
      </div>
      {this.renderFailedTests(build, job_phases)}
      {render_all ? this.renderJobs(build, job_phases) : null}
      {render_all ?
      <div className="marginTopL">
        <a href={`/code/${build.source.id}`}>View Code for this Build</a>
      </div>
      : null}
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

  renderButtons: function(build) {
    var cancel = get_runnable_condition(build) === 'waiting' ?
      <div className="marginTopM">
        <Request
          parentElem={this}
          name="cancelBuild"
          method="post"
          endpoint={`/api/0/builds/${build.id}/cancel/`}>
          <Button type="white" className="sizedButton">
            <span className="red">
              <i className="fa fa-ban marginRightM" />
              Cancel Build
            </span>
          </Button>
        </Request>
      </div> :
      null;

    var unsafe_to_push = null;

    // only admins can mark a build as unsafe to push
    if (window.changesAuthData && window.changesAuthData.user && window.changesAuthData.user.isAdmin === true){
      // if already marked unsafe, allow it to be marked as safe again
      var build_tags = "";

      var build_tags = build.tags.filter(x => x !== "unsafe_to_push").map(x => "tags="+x).join("&")

      if (!("unsafe_to_push" in build.tags)){
        build_tags += "&tags=unsafe_to_push";
      }

      if ("unsafe_to_push" in build.tags){
        var unsafeName = "markBuildSafe";
        var buttonText = "Mark Safe";
        var buttonColor = "";
        var buttonClass = "fa fa-check marginRightM";
      // otherwise, allow user to mark as unsafe
      } else {
        var unsafeName = "markBuildUnsafe";
        var buttonText = "Mark Unsafe";
        var buttonColor = "red";
        var buttonClass = "fa fa-minus-circle marginRightM";
      }

      var unsafe_to_push =
        <div className="marginTopM">
          <Request
            parentElem={this}
            name={unsafeName}
            endpoint={`/api/0/builds/${build.id}/tags?${build_tags}`}>
            <Button type="white" className="sizedButton">
              <span className={buttonColor}>
                <i className={buttonClass} />
                {buttonText}
              </span>
            </Button>
          </Request>
        </div>
    }


    // show a button for the tests for build page, since its important and we
    // want a prominent link
    var buildTestsHref = `/build_tests/${build.id}` +
      (build.testFailures.total > 0 ? '' : "#SlowTests")

    return <div>
      <Request
        parentElem={this}
        name="recreateBuild"
        method="post"
        endpoint={`/api/0/builds/${build.id}/retry/`}>
        <Button type="white" className="sizedButton">
          <i className="fa fa-repeat marginRightM" />
          Recreate Build
        </Button>
      </Request>
      {cancel}
      <div className="marginTopM">
        <Button
          type="white"
          className="sizedButton"
          href={buildTestsHref}>
          <i className="fa fa-ellipsis-h marginRightM" />
          Test Details
        </Button>
      </div>
      {unsafe_to_push}
    </div>;
  },

  renderDetails: function(build, job_phases) {
    var attributes = {};
    attributes['Created'] = formatTime(build.dateCreated);
    if (build.dateStarted) {
      attributes['Started'] = formatTime(build.dateStarted);
    }
    if (build.dateFinished) {
      attributes['Finished'] = (
        formatTime(build.dateFinished) +
        ` (${display_duration(build.duration / 1000)})`
      );
    }

    var testCount = (!build.stats.test_count && get_runnable_condition(build) === 'waiting') ?
      'In Progress' : build.stats.test_count;

    var testLabel = build.dateFinished ? "Tests Ran" : "Tests Run";
    var buildTestsHref = `/build_tests/${build.id}` +
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
        You can retry it using the button on the right.
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
      var href = `/project_test/${test.project.id}/${test.hash}`;

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
        display_duration(test.duration / 1000),
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
        <a href={"/build_tests/"+build.id+"/"}>
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
        colnum={3}
        className="marginBottomM"
        data={rows}
        headers={['Name', 'Links', 'Duration']}
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

      // Sort the list of job steps.
      let steps = phase.steps.slice();
      steps.sort((a, b) => {
        // Test failures at the top.
        let test_difference = (b.testFailures || 0) - (a.testFailures || 0);
        if (test_difference) {
          return test_difference;
        }

        // Other failures after test failures.
        let status_a = get_runnable_condition(a).search('failed');
        let status_b = get_runnable_condition(b).search('failed');
        if (status_a !== status_b) {
          return status_b - status_a;
        }

        // Fallback to sorting by finish time (builds finished most recently at the top).
        // Note that dateFinished may be undefined if the step is not yet complete.
        // Such steps will be sorted above completed steps.
        let date_a = Date.parse(a.dateFinished) || 0;
        let date_b = Date.parse(b.dateFinished) || 0;
        return date_a - date_b;
      });

      // we sometimes rerun jobsteps multiple times. Rearrange them so that
      // jobsteps that were rerun are always together.

      // partition into non-replaced and replaced jobsteps
      var [grouped_steps, remaining_steps] = _.partition(steps, step => {
        return step.replacement_id == null;
      });
      // now we go through each replaced step and group it with its
      // replacement, repeating this process as necessary.
      var remaining = remaining_steps.length;
      while (remaining) {
        remaining_steps = _.filter(remaining_steps, step => {
          let index = _.findIndex(grouped_steps, replacement => {
            return replacement.id == step.replacement_id;
          });
          if (index == -1) {
            // this step's replacement isn't in grouped_steps yet, keep trying
            return true;
          }
          grouped_steps.splice(index + 1, 0, step);
          return false;
        });
        // make sure we don't loop forever
        if (remaining_steps.length && remaining_steps.length == remaining) {
          grouped_steps.concat(remaining_steps);
          break;
        }
        remaining = remaining_steps.length;
      }

      let phase_rows = [];
      for (let index = 0; index < grouped_steps.length; index++) {
        let jobstep = grouped_steps[index];
        var jobstepCondition = get_runnable_condition(jobstep);
        var jobstepDot = <ConditionDot condition={jobstepCondition} />;

        var timeline = {
          'Created': jobstep.dateCreated,
          'Started': jobstep.dateStarted,
          'Finished': jobstep.dateFinished,
        };
        let formattedTimeline = _.map(timeline, (t, label) => {
          return t ? <div>{label}: {formatTime(t)}</div> : '';
        });

        let expandTimelineOnClick = __ => {
          this.setState(
            utils.update_key_in_state_dict('expandedJobStepTimelines',
              jobstep.id,
              !this.state.expandedJobStepTimelines[jobstep.id])
          );
        };

        let expandTimelineLabel = !this.state.expandedJobStepTimelines[jobstep.id] ?
          'details' : 'collapse';

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
          jobstepDuration = <div>
            {jobstepDuration}{' ('}<a onClick={expandTimelineOnClick}>{expandTimelineLabel}</a>{')'}
            {this.state.expandedJobStepTimelines[jobstep.id] ? formattedTimeline : ''}
          </div>;
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

        var jobstepImage = '';
        if (jobstep.image) {
            var imageLabel = jobstep.image.id.substring(0, 8);
            var staleness = moment.utc(jobstep.dateCreated).from(moment.utc(jobstep.image.dateCreated), true);
            jobstepImage = <div><SimpleTooltip label={staleness + " old when used"} placement="right">
                    <a href={ChangesLinks.snapshotImageHref(jobstep.image)}>{imageLabel}</a>
                </SimpleTooltip></div>;
        }

        if (!jobstep.node) {
          phase_rows.push(new GridRow([
            index === 0 && !only_one_row ?
              <span className="lb">{phase.name}</span> : "",
            jobstepDot,
            jobstepImage,
            <div>
              <i>Machine not yet assigned</i>
              {failureMarkup}
            </div>,
            '',
            jobstepDuration
          ]));
          continue;
        }

        var replacementMarkup = null;
        if (jobstep.replacement_id != null) {
          replacementMarkup = <div className="marginTopS mediumGray">
            <i>Retried.</i>
          </div>;
        }

        var links = [];
        var nodeLink = jobstep.node.name || jobstep.node.id;
        var chunkedUrls = [];
        jobstep.logSources.forEach(l => {
          l.urls.forEach(logSourceURL => {
            if (logSourceURL.type == "chunked") {
              var log_uri = `/job_log/${build.id}/${job.id}/${l.id}/`;
              chunkedUrls.push(log_uri);
            } else {
              links.push(<a className="external marginRightM" href={logSourceURL.url} target="_blank">{l.name}</a>);
            }
          })
        });

        // First, check if there is at least one "chunked" (tail-able) URL.
        // If yes, link the first one from the node id (currently, we're guaranteed to only have one
        // url of this kind, till artifacts store exposes such a url).
        // TODO(anupc): Figure out a good way to display more than one link of this form.
        if (chunkedUrls.length >= 1) {
          nodeLink = <a href={chunkedUrls[0]}>{nodeLink}</a>;
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

        let onClick = __ => {
          this.setState(
            utils.update_key_in_state_dict('expandedJobSteps',
              jobstep.id,
              !this.state.expandedJobSteps[jobstep.id])
          );
        };

        let expandLabel = !this.state.expandedJobSteps[jobstep.id] ?
          'Expand' : 'Collapse';


        // no separator and 50% opacity for replaced jobstep
        var hasBorder = jobstep.replacement_id == null;
        var fadedOut = jobstep.replacement_id != null;
        phase_rows.push(new GridRow([
          index === 0 && !only_one_row ?
            <span className="lb">{phase.name}</span> :
            "",
          jobstepDot,
          jobstepImage,
          <div>{nodeLink}{failureMarkup}{replacementMarkup}<a onClick={onClick}>{expandLabel}</a></div>,
          links,
          jobstepDuration,
        ], hasBorder, fadedOut));

        if (this.state.expandedJobSteps[jobstep.id]) {
          phase_rows.push(GridRow.oneItem(<JobstepDetails jobstepID={jobstep.id} />));
        }
      }
      return phase_rows;
    });

    var job_headers = [
      'Phase',
      'Result',
      'Snapshot Image',
      'Machine Log',
      'Links',
      'Duration',
    ];

    var cellClasses = [
      'nowrap phaseCell', 'nowrap center', 'nowrap', 'wide', 'nowrap', 'nowrap',
    ];

    return <Grid
      colnum={6}
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
    pageElem: PropTypes.object,
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
        <div style={{ fontSize: 18 }}>Summary: Latest Builds per Project</div>
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
