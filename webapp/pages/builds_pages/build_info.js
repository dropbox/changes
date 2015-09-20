import React, { PropTypes } from 'react';
import moment from 'moment';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesLinks from 'es6!display/changes/links';
import SectionHeader from 'es6!display/section_header';
import { AjaxError } from 'es6!display/errors';
import { Button } from 'es6!display/button';
import { ConditionDot, get_runnable_condition, get_runnables_summary_condition, get_build_cause, get_cause_sentence } from 'es6!display/changes/builds';
import { Grid, GridRow } from 'es6!display/grid';
import { InfoList, InfoItem } from 'es6!display/info_list';
import { display_duration } from 'es6!display/time';

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
      // used by the recreate build button
      recreateBuild: null,

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

    var header_subtext = '';
    if (condition.indexOf("failed") === 0) {
      var failed_test_count = build.stats.test_failures;
      var error_count = _.filter(build.failures, f => f.id !== 'test_failures').length;

      var failed_test_sentence = utils.plural(
        failed_test_count, 'test(s) failed. ', true, true);

      var error_sentence = error_count > 0 ?
        utils.plural(error_count, 'error message(s)') : '';

      header_subtext = <div className="red">
        {failed_test_sentence}{error_sentence}
      </div>;
    } else if (condition.indexOf === "waiting") {
      header_subtext = <div className="mediumGray">
        Have run {build.stats.test_count} test(s) in{" "}
        {display_duration(moment.utc().diff(moment.utc(build.dateCreated), 's'))}
      </div>;
    } else {
      header_subtext = <div className="mediumGray">
        Ran {utils.plural(build.stats.test_count, " test(s) ")} in{" "}
        {display_duration(build.duration / 1000)}
      </div>;
    }

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
        <div style={{ fontSize: 18 }}>{build.project.name}</div>
        {header_subtext}
      </div>
      <div className="marginTopS">
        {get_cause_sentence(get_build_cause(build))}
      </div>
    </div>;
  },

  renderButton: function(build) {
    var recreate = this.state.recreateBuild;

    if (recreate && recreate.condition === 'loading') {
      return <div>
        <i className="fa fa-spinner fa-spin" />
      </div>;
    } else if (api.isError(recreate)) {
      return <AjaxError response={recreate.response} />;
    } else if (api.isLoaded(recreate)) {
      // reload to pick up the new build
      window.location.reload();
    }

    var onClick = evt => {
      api.post(this, {
        recreateBuild: `/api/0/builds/${build.id}/retry/`
      });
    };

    return <Button
      type="white"
      onClick={onClick}>
      <i className="fa fa-repeat marginRightS" />
      Recreate Build
    </Button>;
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

    var testLabel = build.dateFinished ? "Tests Ran" : "Tests Run";
    var buildTestsHref = `/v2/build_tests/${build.id}` +
      (build.testFailures.total > 0 ? '' : "#SlowTests")
    attributes[testLabel] = <span>
      {build.stats.test_count}{" ("}
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

        if (!this.state.expandedTestsData[test.id]) {
          api.fetchMap(this, 'expandedTestsData', {
            [ test.id ]: `/api/0/tests/${test.id}/`
          });
        }
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
        if (!api.isLoaded(this.state.expandedTestsData[test.id])) {
          rows.push(GridRow.oneItem(
            <APINotLoaded
              className="marginTopM"
              calls={this.state.expandedTestsData[test.id]}
            />
          ));
        } else {
          var data = this.state.expandedTestsData[test.id].getReturnedData();
          rows.push(GridRow.oneItem(
            <div className="marginTopS">
              <b>Captured Output</b>
              <pre className="defaultPre">
              {data.message}
              </pre>
            </div>
          ));
        }
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
      // what the server calls a jobstep is better named as shard
      return _.map(phase.steps, (shard, index) => {
        var shard_state = get_runnable_condition(shard);
        var shard_duration = 'Running';
        if (shard_state !== 'waiting') {
          shard_duration = shard.duration ?
            display_duration(shard.duration/1000) : '';
        }

        if (!shard.node) {
          return [
            index === 0 && !only_one_row ?
              <span className="lb">{phase.name}</span> : "",
            <ConditionDot state={shard_state} />,
            <i>Machine not yet assigned</i>,
            '',
            shard_duration
          ];
        }
        var node_name = <a href={"/v2/node/" + shard.node.id}>
          {shard.node.name}
        </a>;

        var shard_failures = _.filter(failures, f => f.step_id == shard.id);

        var main_markup = node_name;
        if (shard_failures) {
          var failure_markup = _.map(shard_failures, f => {
            var reason = f.reason;
            if (f.id === 'test_failures') {
              // Note: the failure message itself doesn't tell us the correct
              // number of failing tests. I modified the API we use to send the
              // correct number as a separate param
              reason = 'Some tests failed';
              if (shard.testFailures && shard.testFailures > 0) {
                reason = utils.plural(shard.testFailures, 'test(s) failed');
              }
            }

            return <div className="red">{reason}</div>;
          });

          main_markup = <div>
            {node_name}
            <div className="marginTopS">{failure_markup}</div>
          </div>
        }

        var links = [];

        var log_id = shard.logSources[0] && shard.logSources[0].id;
        if (log_id) {
          var log_uri = `/v2/job_log/${build.id}/${job.id}/${log_id}/`;
          links.push(<a className="marginRightM" href={log_uri}>Log</a>);

          var raw_log_uri = `/api/0/jobs/${job.id}/logs/${log_id}/?raw=1`;
          links.push(<a className="external marginRightM" href={raw_log_uri} target="_blank">Raw</a>);
        }
        if (shard.data.uri) {
          links.push(<a className="external" href={shard.data.uri} target="_blank">Jenkins</a>);
        }

        return [
          index === 0 && !only_one_row ?
            <span className="lb">{phase.name}</span> : "",
          <ConditionDot condition={shard_state} />,
          main_markup,
          links,
          shard_duration
        ];
      });
    });

    var job_headers = [
      'Phase',
      'Result',
      'Machine',
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
    var latest_by_proj = _.chain(builds)
      .groupBy(b => b.project.name)
      .map(proj_builds => _.last(_.sortBy(proj_builds, b => b.dateCreated)))
      .values()
      .value();

    var summary_condition = get_runnables_summary_condition(latest_by_proj);
    builds = _.map(latest_by_proj, (b, index) => {
      return <div className="marginTopL paddingTopL fainterBorderTop">
        <SingleBuild build={b} content="short" />
      </div>
    });

    return <div>
      {this.renderHeader(latest_by_proj)}
      {builds}
    </div>;
  },

  renderHeader: function(latest_by_proj) {
    var summary_condition = get_runnables_summary_condition(latest_by_proj);

    var subtext = '';
    var subtext_extra_class = '';
    if (summary_condition.indexOf('failed') === 0) {
      var failing = _.filter(latest_by_proj,
        b => get_runnable_condition(b).indexOf('failed') === 0);
      subtext = `${failing.length} out of ${utils.plural(latest_by_proj.length, 'project(s)')} failed`;
      subtext_extra_class = 'redGrayMix';
    } else if (summary_condition === 'waiting') {
      var waiting = _.filter(latest_by_proj,
        b => get_runnable_condition(b) === 'waiting');
      subtext = `${waiting.length} out of ${utils.plural(latest_by_proj.length, 'project(s)')} are still running`;
    } else if (summary_condition === 'unknown') {
      var unknown = _.filter(latest_by_proj,
        b => get_runnable_condition(b) === 'unknown');
      subtext = `${unknown.length} out of ${utils.plural(latest_by_proj.length, 'project(s)')} have an unknown status`;
    } else {
      subtext = `${utils.plural(latest_by_proj.length, 'project(s)')} passed`;
    }

    var dot = <ConditionDot
      condition={summary_condition}
      size="large"
      glow={latest_by_proj.length > 1}
    />;

    var style = {
      verticalAlign: 'top',
      marginLeft: 5
    };

    return <div>
      {dot}
      <div className="inlineBlock" style={style}>
        <div style={{ fontSize: 18 }}>Latest Builds</div>
        <div className={subtext_extra_class}>
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
