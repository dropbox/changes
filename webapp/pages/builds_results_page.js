import React from 'react';
import moment from 'moment';

import ChangesPage from 'es6!display/page_chrome';
import * as api from 'es6!server/api';
import APINotLoaded from 'es6!display/not_loaded';
import * as utils from 'es6!utils/utils';
import * as DisplayUtils from 'es6!display/changes/utils';

import { TimeText, display_duration } from 'es6!display/time';
import { StatusDot, get_build_state, get_runnable_state, get_state_color, get_build_cause } from 'es6!display/changes/builds';
import { Error, ProgrammingError } from 'es6!display/errors';
import { Grid, GridRow } from 'es6!display/grid';
import SectionHeader from 'es6!display/section_header';
import { Menu1, Menu2 } from 'es6!display/menus';
import colors from 'es6!utils/colors';
import custom_content_hook from 'es6!utils/custom_content';

var cx = React.addons.classSet;

/* The pages that show the results of builds run on a commit or diff */
// TODO: I need a page that just shows a single build, e.g. for arc test.

/**
 * Page that shows the builds associated with a single diff, for every project.
 * This is inconsistent with the commits page that's scoped to a single page...
 * will change that once I figure out which way is better
 */
export var DiffPage = React.createClass({

  getInitialState: function() {
    return {
      diffBuilds: null,
    }
  },

  componentDidMount: function() {
    var diff_id = this.props.diff_id;
    api.fetch(this, {
      diffBuilds: `/api/0/phabricator_diffs/${diff_id}/builds`
    });
  },

  render: function() {
    if (!api.isLoaded(this.state.diffBuilds)) {
      return <APINotLoaded state={this.state.diffBuilds} />;
    }
    var diff_data = this.state.diffBuilds.getReturnedData();

    // emergency backups in case phabricator is unreachable
    diff_data['revision_id'] = diff_data['revision_id'] || this.props.diff_id.substr(1);
    diff_data['dateCreated'] = diff_data['dateCreated'] || 0; // unix timestamp

    var builds = _.chain(diff_data.changes)
      .pluck('builds')
      .flatten()
      .value();
    
    return <BuildsPage
      type="diff"
      targetData={diff_data}
      builds={builds}
    />;
  }
});

/**
 * Page that shows the builds associated with a single commit within a project
 * (since multiple projects can share a repository, they would each have their
 * own version of this page)
 */
export var CommitPage = React.createClass({

  getInitialState: function() {
    return {
      commitBuilds: null,
      source: null,
    }
  },

  componentDidMount: function() {
    var uuid = this.props.sourceUUID;

    api.fetch(this, {
      commitBuilds: `/api/0/sources/${uuid}/builds`,
      source: `/api/0/sources/${uuid}`
    });
  },

  render: function() {
    var slug = this.props.project;

    if (!api.mapIsLoaded(this.state, ['commitBuilds', 'source'])) {
      return <APINotLoaded 
        stateMap={this.state} 
        stateMapKeys={['commitBuilds', 'source']} 
      />;
    }

    return <BuildsPage
      type="commit"
      targetData={this.state.source.getReturnedData()}
      builds={this.state.commitBuilds.getReturnedData()}
    />;
  }
});

/** ---IMPLEMENTATION--- **/

/**
 * The internal page shared by CommitPage and DiffPage (since the logic is
 * basically the same)
 */
var BuildsPage = React.createClass({

  propTypes: {
    // are we rendering for a diff or a commit
    type: React.PropTypes.oneOf(['diff', 'commit']).isRequired,
    // info about the commit (a changes source object) or diff (from phab.)
    targetData: React.PropTypes.object,
    // the builds associated with this diff/commit. They may be more sparse
    // than a call to build_details...we use this to populate the sidebar
    builds: React.PropTypes.array.isRequired,
  },

  getInitialState: function() {
    var query_params = URI(window.location.href).search(true);

    return {
      activeBuildID: query_params.buildID,
      tests: {}, // fetched on demand
    }
  },

  render: function() {
    var content_style = {
      marginLeft: 300,
    };

    this.updateWindowUrl();

    // TODO: cleanup!
    // padding: "10px 35px", 
    return <ChangesPage bodyPadding={false} fixed={true}>
      <NewSidebar
        builds={this.props.builds}
        type={this.props.type}
        targetData={this.props.targetData}
        activeBuildID={this.state.activeBuildID}
        pageElem={this}
      />
      <div style={{paddingTop: 32}}>
        <div style={content_style} >
          {this.getContent()}
        </div>
      </div>
    </ChangesPage>;
  },

  updateWindowUrl: function() {
    var query_params = URI(window.location.href).search(true);
    if (this.state.activeBuildID && 
        this.state.activeBuildID !== query_params['buildID']) {
      query_params['buildID'] = this.state.activeBuildID;
      window.history.replaceState(
        null,
        'changed tab',
        URI(window.location.href)
          .search(query_params)
          .toString()
      );
    }
  },

  getContent: function() {
    var builds = this.props.builds;

    if (this.state.activeBuildID) {
      var build = _.filter(builds, b => b.id === this.state.activeBuildID);
      if (build) {
        // use a key so that we remount when switching builds
        return {
          [ build[0].id ]:
            <SingleBuild
              build={build[0]}
            />
        };
      }
    }

    // get all builds for latest code
    var latest_builds = builds;

    if (this.props.type === 'diff') {
      var builds_by_diff_id = _.groupBy(
        builds, 
        b => b.source.data['phabricator.diffID']);

      var latest_diff_id = _.chain(builds)
        .keys()
        .sortBy()
        .last()
        .value();

      latest_builds = builds_by_diff_id[latest_diff_id];
    }

    return _.map(latest_builds, b => <SingleBuild build={b} />);
  }
});

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
        var shard_state = get_runnable_state(shard.status.id, shard.result.id);
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

// Sidebar

var NewSidebar = React.createClass({

  propTypes: {
    // list of builds to render in side bar
    builds: React.PropTypes.array,
    // are we rendering for a diff or a commit
    type: React.PropTypes.oneOf(['diff', 'commit']),
    // if its a diff, grab its information
    targetData: React.PropTypes.object,
    // which build are we currently showing, if any
    activeBuildID: React.PropTypes.string,
    // the parent page element. Sidebar clicks change its state
    pageElem: React.PropTypes.element,
  },

  render: function() {
    return <div className="buildsSidebar">
      {this.renderHeader()}
      {this.renderBuildsList()}
      {this.renderSurroundingBuilds()}
      {this.renderOtherActions()}
    </div>;
  },

  renderHeader: function() {
    var type = this.props.type;

    var header = "No header yet";
    if (type === 'commit') {
      var source = this.props.targetData;
      header = <div>
        {source.revision.sha.substring(0,7)}{": "}
        {utils.first_line(source.revision.message)}
      </div>;
    } else if (type === 'diff') {
      var diff_data = this.props.targetData;
      header = <div>
        <a className="subtle" href={diff_data.uri} target="_blank">
          D{diff_data.id}
        </a>
        {": "}
        {diff_data.title}
      </div>;
    } else {
      throw 'unreachable';
    }

    return <div style={{fontWeight: 'bold', padding: 10}}>
      {header}
    </div>;
  },

  renderBuildsList: function() {
    var type = this.props.type;

    var content = "No content yet";
    if (type === 'commit') {
      content = this.renderBuildsForCommit();
    } else if (type === 'diff') {
      content = this.renderBuildsForDiff();
    } else {
      throw 'unreachable';
    }

    return <div>
      {content}
    </div>;
  },

  renderBuildsForCommit: function() {
    var builds = this.props.builds,
      source = this.props.targetData;

    console.log(source);
    var label = <span>
      Committed {"("}<TimeText time={source.revision.dateCommitted} />{")"}
    </span>;
    var content = this.renderBuilds(builds);
    
    return this.renderSection(label, content);
  },

  renderBuildsForDiff: function() {
    // the main difference between diffs and commits is that diffs may have
    // multiple, distinct code changes, each of which have their own builds.
    // We want one section for each diff update
    var builds = this.props.builds,
      diff_data = this.props.targetData;

    var builds_by_update = _.groupBy(builds, b => b.source.data['phabricator.diffID']);

    var all_diff_ids = _.sortBy(diff_data.diffs).reverse();
    // one of those diff updates is the original diff that was sent
    var original_single_diff_id = _.last(all_diff_ids);

    var sections = [];
    _.each(all_diff_ids, (single_diff_id, index) => {
      var builds = builds_by_update[single_diff_id];
      var changes_data = diff_data.changes[single_diff_id];

      var diff_update_num = all_diff_ids.length - index - 1;

      if (single_diff_id > original_single_diff_id) {
        if (changes_data) {
          var section_header = <span>
            Diff Update #{diff_update_num}
            {" ("}
            <TimeText time={moment.utc(changes_data['dateCreated'])} />
            {")"}
          </span>;
        } else {
          var section_header = <span>Diff Update #{diff_update_num}</span>
        }
      } else {
        var section_header = <span>
          Created D{diff_data.id}{" ("}
          <TimeText time={moment.unix(diff_data.dateCreated).toString()} />
          {")"}
        </span>;
      }
      var section_content = builds ? this.renderBuilds(builds) : null;

      sections.push(this.renderSection(section_header, section_content));
    });
    return sections;
  },

  renderBuilds: function(builds) {
    if (builds === undefined) {
      return null;
    }
    builds = _.chain(builds)
      .sortBy(b => b.dateCreated)
      .reverse()
      .value();

    var time_style = {
      float: 'right',
      marginRight: 10,
      color: '#333'
    };

    var on_click = build_id => {
      return evt => {
        this.props.pageElem.setState({
          activeBuildID: build_id
        });
      };
    };

    var entries = _.map(builds, b => {
      var build_state = get_build_state(b);

      var classes = "buildsSideItem";
      if (this.props.activeBuildID === b.id) {
        classes += " lt-lightgray-bg";
      }

      var failed = null;
      if (build_state === 'failed' || build_state === 'nothing') {
        failed = <div className="lt-red" style={{marginTop: 3}}>
          {b.stats.test_failures} tests failed
        </div>
      }

      return <div className={classes} onClick={on_click(b.id)}>
        <div style={{display: 'inline-block'}}>{b.project.name}</div>
        <div style={time_style}>{display_duration(b.duration / 1000)}</div>
        <div className="subText">
          Triggered by {get_build_cause(b)}
          {", "}
          {b.stats.test_count} tests
        </div>
        {failed}
      </div>
    });

    return <div>
      {entries}
    </div>;
  },

  renderSurroundingBuilds: function() {
    // TODO
    return null;

    if (this.props.type === "diff") {
      return null;
    }
    return this.renderSection("Nearby Commits", <span>TODO</span>);
  },

  renderOtherActions: function() {
    return this.renderSection(
      'Other Actions',
      <a className="buildsSideItem">
        Create New Build [TODO]
      </a>
    );
  },

  renderSection: function(header, content) {
    return <div className="marginTopL">
      <div className="buildsSideSectionHeader">{header}</div>
      <div>{content}</div>
    </div>;
  }
});

var hash_id = function(id) { return "s_" + id; }
var hash_href = function(id) { return "#" + hash_id(id); }
