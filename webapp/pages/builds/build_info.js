import React, { PropTypes } from 'react';
import moment from 'moment';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesLinks from 'es6!display/changes/links';
import SectionHeader from 'es6!display/section_header';
import { ConditionDot, get_runnable_condition, get_runnables_summary_condition, get_build_cause } from 'es6!display/changes/builds';
import { Grid, GridRow } from 'es6!display/grid';
import { InfoList, InfoItem } from 'es6!display/info_list';
import { display_duration } from 'es6!display/time';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';
import custom_content_hook from 'es6!utils/custom_content';

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
    //
    content: PropTypes.oneOf(['short', 'normal'])
  },

  getDefaultProps: function() {
    return {
      content: 'normal'
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
      endpoint_map[id] = `/api/0/jobs/${id}/phases`;
    });

    // TODO: don't refetch every time (cache on parent)
    api.fetchMap(this, 'jobPhases', endpoint_map);
  },

  getInitialState: function() {
    return {
      // states for toggling inline visibility
      showRevertInstructions: {},
      expandedTests: {},
      expandedTestsData: {}
    };
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
      {this.renderHeader(build, job_phases)}
      {this.renderFailedTests(build, job_phases)}
      {render_all ? this.renderBuildDetails(build, job_phases) : null}
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

    return <div className="marginBottomL">
      {dot}
      <div className="inlineBlock" style={style}>
        <div style={{ fontSize: 18 }}>{build.project.name}</div>
        {header_subtext}
      </div>
      <div className="marginTopS">
        This trigger for this build was{" "}
        <span color="mediumGray">
        {get_build_cause(build)}
        </span>{"."}
      </div>
    </div>;
  },

  renderBuildDetails: function(build, job_phases) {
    // split attributes into a left and right column
    var attributes_left = {};
    attributes_left['By'] = ChangesLinks.author(build.author);
    attributes_left['Trigger'] = get_build_cause(build);
    attributes_left['Project'] = ChangesLinks.project(build.project);
    attributes_left['Test Count'] = build.stats.test_count;
    attributes_left['Duration'] = display_duration(build.duration/1000);

    var DATE_RFC2822 = "ddd, DD MMM YYYY HH:mm:ss ZZ";

    var attributes_right = {};
    attributes_right['Status'] = build.status.name;
    attributes_right['Result'] = build.result.name;
    attributes_right['Time Started'] = build.dateCreated && moment.utc(build.dateCreated).format(DATE_RFC2822);
    attributes_right['Time Completed'] = build.dateFinished && moment.utc(build.dateFinished).format(DATE_RFC2822);
    attributes_right['Build Number'] = build.number;

    var attributes_to_table = attr => {
      var rows = _.map(attr, (v,k) => <InfoItem label={k}>{v}</InfoItem>);
      return <InfoList>{rows}</InfoList>;
    };

    var column_style = {
      width: '49%', 
      display: 'inline-block', 
      verticalAlign: 'top'
    };

    return <div>
      <SectionHeader>Details</SectionHeader>
      <div>
        <div style={column_style}>
          {attributes_to_table(attributes_left)}
        </div>
        <div style={column_style}>
          {attributes_to_table(attributes_right)}
        </div>
      </div>
    </div>
  },

  // which tests caused the build to fail?
  renderFailedTests: function(build, job_phases) {
    if (build.testFailures.total <= 0) {
      return null;
    }

    var rows = [];
    _.each(build.testFailures.tests, test => {
      var split_char = test.name.indexOf('/') >= 0 ? '/' : '.';
      var simple_name = _.last(test.name.split(split_char));
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

      var markup = [
        <div>
          {simple_name} <a onClick={onClick}>Expand</a>
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

    var revert_instructions = custom_content_hook('revertInstructions');
    var revert_markup = null, revert_link = null;
    if (revert_instructions) {
      var on_click = __ => {
        this.setState((prevStat, props) => {
          var instr = _.clone(prevStat.showRevertInstructions);
          instr[build.id] = !instr[build.id];
          return {showRevertInstructions: instr};
        });
      };
      revert_link = <div className="darkGray marginTopM">
        How do I{" "}
        <a onClick={on_click}>revert this</a>?
      </div>

      if (this.state.showRevertInstructions[build.id]) {
        revert_markup = <pre className="defaultPre">
          {custom_content_hook('revertInstructions')}
        </pre>;
      }
    }

    // TODO: see all
    var more_markup = null;
    if (build.testFailures.total > build.testFailures.tests.length) {
      more_markup = <div className="darkGray marginTopM">
        Only showing
        {" "}{build.testFailures.tests.length}{" "}
        out of
        {" "}{build.testFailures.total}{" "}
        failed tests.
      </div>
    }

    return <div className="marginTopL">
      <SectionHeader>Failed Tests</SectionHeader>
      <Grid
        colnum={2}
        className="errorGrid marginBottomM"
        data={rows}
        headers={['Name', 'Links']}
      />
      {more_markup}
      {revert_link}
      {revert_markup}
    </div>;
  },

  // what did the build actually do?
  renderJobs: function(build, phases) {
    var markup = _.map(build.jobs, (job, index) => {
      // we'll render a table with content from each phase
      return <div className="marginTopL">
        <b>Build Plan:{" " + job.name}</b>
        {this.renderJobTable(job, build, phases)}
      </div>;
    });

    return <div className="marginTopL">
      <SectionHeader>Breakdown</SectionHeader>
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
              reason = f.reason.match(/\d+ failing tests/);
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
      'nowrap', 'nowrap center', 'wide', 'nowrap', 'nowrap'
    ];

    return <Grid
      colnum={5}
      className="marginTopS"
      data={_.flatten(phases_rows, true)}
      headers={job_headers}
      cellClasses={cellClasses}
    />;
  }
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
