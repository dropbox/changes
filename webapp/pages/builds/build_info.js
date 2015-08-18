import React from 'react';
import moment from 'moment';

import APINotLoaded from 'es6!display/not_loaded';
import DisplayUtils from 'es6!display/changes/utils';
import SectionHeader from 'es6!display/section_header';
import { Grid, GridRow } from 'es6!display/grid';
import { StatusDot, get_runnable_state, get_build_cause } from 'es6!display/changes/builds';
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
var SingleBuild = React.createClass({

  propTypes: {
    // the build to render
    build: React.PropTypes.object,
  },

  componentDidMount: function() {
    // get richer information about the build
    console.log(this.props.build);
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

    if (!api.mapIsLoaded(this.state.jobPhases, job_ids)) {
      return <APINotLoaded
        className="marginTopL"
        stateMap={this.state.jobs}
        stateMapKeys={job_ids}
        isInline={true}
      />;
    } else if (!api.isLoaded(this.state.buildDetails)) {
      return <APINotLoaded
        className="marginTopL"
        state={this.state.buildDetails}
        isInline={true}
      />;
    }

    var build = this.state.buildDetails.getReturnedData();

    var job_phases = _.mapObject(this.state.jobPhases, (v,k) => {
      return v.getReturnedData();
    });

    return <div className="paddingTopM marginRightM">
      {this.renderBuildDetails(build, job_phases)}
      {this.renderFailedTests(build, job_phases)}
      {this.renderJobs(build, job_phases)}
    </div>;
  },

  renderBuildDetails: function(build, job_phases) {
    // split attributes into a left and right column
    var attributes_left = {};
    attributes_left['By'] = DisplayUtils.authorLink(build.author);
    attributes_left['Cause'] = get_build_cause(build);
    attributes_left['Project'] = DisplayUtils.projectLink(build.project);
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
      var rows = _.map(attr, (v,k) => {
        return <tr>
          <td><b>{k}:</b></td>
          <td>{v}</td>
        </tr>
      });
      return <table className="invisibleTable">{rows}</table>;
    };

    return <div>
      <SectionHeader>Details</SectionHeader>
      <div>
        <div style={{width: '49%', display: 'inline-block'}}>
          {attributes_to_table(attributes_left)}
        </div>
        <div style={{width: '49%', display: 'inline-block'}}>
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
      var simple_name = _.last(test.name.split("."));
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
              state={this.state.expandedTestsData[test.id]}
              isInline={true}
            />
          ));
        } else {
          var data = this.state.expandedTestsData[test.id].getReturnedData();
          rows.push(GridRow.oneItem(
            <div className="marginTopS">
              <b>Captured Output</b>
              <pre className="yellowPre">
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
      revert_link = <span>{" ["}
        <a onClick={on_click}>How do I revert this?</a>
      {"]"}</span>;

      if (this.state.showRevertInstructions[build.id]) {
        revert_markup = <pre className="yellowPre">
          {custom_content_hook('revertInstructions')}
        </pre>;
      }
    }

    // TODO: see all
    var more_markup = null;
    if (build.testFailures.total > build.testFailures.tests.length) {
      more_markup = <div className="lt-darkgray marginTopM">
        Only showing
        {" "}{build.testFailures.tests.length}{" "}
        out of
        {" "}{build.testFailures.total}{" "}
        failed tests.
      </div>
    }

    return <div className="marginTopL">
      <div>
        <SectionHeader className="inlineBlock">Failed Tests</SectionHeader>
        {revert_link}
      </div>
      {revert_markup}
      <Grid
        colnum={2}
        className="errorGrid marginBottomM"
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
      return <div>
        {render_subheader(job.name)}
        {this.renderJobTable(job, build, phases)}
      </div>;
    });

    return <div className="marginTopL">
      <SectionHeader>Breakdown</SectionHeader>
      {markup}
    </div>;
  },

  renderJobTable: function(job, build, phases) {
    var failures = _.filter(build.failures, f => f.job_id == job.id);
    console.log(failures);
    var phases_rows = _.map(phases[job.id], (phase, index) => {
      // what the server calls a jobstep is better named as shard
      return _.map(phase.steps, (shard, index) => {
        var shard_state = get_runnable_state(shard);
        var shard_duration = 'Running';
        if (shard_state !== 'waiting') {
          shard_duration = shard.duration ?
            display_duration(shard.duration/1000) : '';
        }

        if (!shard.node) {
          return [
            index === 0 ? <b>{phase.name}</b> : "",
            <StatusDot state={shard_state} />,
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
            return <div className="lt-red">{reason}</div>;
          });

          main_markup = <div>
            {node_name}
            <div className="marginTopS">{failure_markup}</div>
          </div>
        }

        var links = [];

        var log_id = shard.logSources[0] && shard.logSources[0].id;
        if (log_id) {
          var slug = build.project.slug;
          var old_log_uri = `/projects/${slug}/builds/${build.id}/jobs/${job.id}/logs/${log_id}/`;
          links.push(<a className="marginRightS" href={old_log_uri} target="_blank">
            Log
            <i style={{marginLeft: 3, opacity: 0.5}} className="fa fa-backward" />
          </a>);

          var raw_log_uri = `/api/0/jobs/${job.id}/logs/${log_id}/?raw=1`;
          links.push(<a className="external marginRightS" href={raw_log_uri} target="_blank">Raw</a>);
        }
        if (shard.data.uri) {
          links.push(<a className="external" href={shard.data.uri} target="_blank">Jenkins</a>);
        }

        return [
          index === 0 ? <b>{phase.name}</b> : "",
          <StatusDot state={shard_state} />,
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

var render_section = function(id, content) {
  var style = {
    padding: 20,
    paddingLeft: 10
  };

  return <div style={style} id={id}>
    {content}
  </div>;
}

var render_header = function(text, moment_time) {
  var header_style = {
    paddingBottom: 4,
  };

  var header_text_style = {
    fontSize: 22,
    fontWeight: "bold"
  };

  var time_style = {
    color: "#5a5758",
    fontSize: "smaller",
    marginBottom: 15
  };

  // right now, this is null if a build hasn't started
  var time = "No time info";
  if (moment_time) {
    time = moment_time.local().format('llll') +
      " (" +
      moment_time.local().fromNow() +
      ")";
  }

  // TODO: cleanup
  return <div>
    <div style={header_style}>
      <div style={header_text_style}>{text}</div>
    </div>
    <div style={time_style}>
      {time}
    </div>
  </div>;
}

var render_subheader = function(text, extra_link) {
  var style = {
    fontSize: 18,
    fontWeight: "bold",
  };

  var extra_markup = [];
  if (extra_link) {
    extra_markup = [" (", extra_link, ")"];
  }

  return <div className="marginTopM">
    <span style={style}>{text}</span>
    {extra_markup}
  </div>;
}

export default SingleBuild;
