import React from 'react';
import moment from 'moment';

import ChangesPage from 'es6!display/page_chrome';
import * as api from 'es6!server/api';
import APINotLoaded from 'es6!display/not_loaded';
import * as utils from 'es6!utils/utils';
import * as display_utils from 'es6!display/changes/utils';

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

    var endpoint = `/api/0/phabricator_diffs/${diff_id}/builds`;
    api.fetch(this, {
      diffBuilds: endpoint
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

    var build_ids = _.chain(diff_data.changes)
      .pluck('builds')
      .flatten()
      .map(b => b.id)
      .value();
    
    return <BuildsResultsPage
      type="diff"
      diffData={diff_data}
      buildIDs={build_ids}
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
    }
  },

  componentDidMount: function() {
    var slug = this.props.project;
    var uuid = this.props.sourceUUID;

    var endpoint = `/api/0/projects/${slug}/sources/${uuid}/builds`;

    api.fetch(this, {
      commitBuilds: endpoint
    });
  },

  render: function() {
    var slug = this.props.project;

    if (!api.isLoaded(this.state.commitBuilds)) {
      return <APINotLoaded state={this.state.commitBuilds} />;
    }

    var build_ids = _.map(this.state.commitBuilds.getReturnedData(), b => b.id);

    return <BuildsResultsPage
      type="commit"
      specificProject={slug}
      buildIDs={build_ids}
    />;
  }
});

/** ---IMPLEMENTATION--- **/

/**
 * The internal page shared by CommitPage and DiffPage (since the logic is
 * basically the same)
 *
 * Apologies for the double-plural, but it is the most accurate name...
 */
var BuildsResultsPage = React.createClass({

  propTypes: {
    // are we rendering for a diff or a commit
    type: React.PropTypes.oneOf(['diff', 'commit']).isRequired,
    // if its a diff, grab its information
    diffData: React.PropTypes.object,
    // are we only rendering data for a specific project. slug if yes, null if no
    specificProject: React.PropTypes.string,
    // the build ids associated with this diff/commit
    buildIDs: React.PropTypes.array.isRequired,
  },

  getInitialState: function() {
    return {
      builds: {},
      jobs: {},

      tests: {}, // fetched on demand

      // states for toggling inline visibility
      showRevertInstructions: {},
      expandedTests: {}
    }
  },

  componentDidMount: function() {
    // we have to do multiple rounds of data fetching because our api sucks, so
    // we do it in render
    this.fetchedBuilds = false;
    this.fetchedJobs = false;

    // if a method encounters something icky (e.g. we don't seem to have picked
    // up a phabricator diff update), store it here. This is not the same as
    // the errors within builds for issues like provision failures
    this.warnings = [];
  },

  finishFetchingData: function() {
    // Hey, we need to do more data fetching. One call per build, then one 
    // call per job (!) Joy. Called from render(), returns either a react 
    // component (loading message) or the fetched data
    // TODO: combine this all into one server-side api call

    // We're using instance variables here to ensure we dispatch these api
    // fetches exactly once. Its a rare but legitimate use of them.

    var build_ids = this.props.buildIDs;

    // Fetch more information about each build

    if (!this.fetchedBuilds) {
      var endpoint_map = {};
      _.each(build_ids, id => {
        endpoint_map[id] = `/api/0/builds/${id}`;
      });

      utils.async(
        api.fetchMap.bind(this, this, 'builds', endpoint_map)
      );

      this.fetchedBuilds = true;
    }

    if (!api.mapIsLoaded(this.state.builds, build_ids)) {
      return <div>
        (1/3){" "}
        <div className="inlineBlock">
          <APINotLoaded stateMap={this.state.builds} />
        </div>
      </div>;
    }
      
    var builds = _.map(this.state.builds, (v, k) => v.getReturnedData());
    
    // Alright, we have a list of builds. Now for jobs.
    // this api returns data about each phase within a job, but not any info
    // about the job itself (that was already fetched in builds above)

    var job_ids = [];
    _.each(builds, b => {
      _.each(b.jobs, j => {
        job_ids.push(j.id);
      });
    });

    if (!this.fetchedJobs) {
      var endpoint_map = {};
      _.each(job_ids, id => {
        endpoint_map[id] = `/api/0/jobs/${id}/phases`;
      });

      utils.async(
        api.fetchMap.bind(this, this, 'jobs', endpoint_map)
      );

      this.fetchedJobs = true;
    }

    if (!api.mapIsLoaded(this.state.jobs, job_ids)) {
      return <div>
        (2/3){" "}
        <div className="inlineBlock">
          <APINotLoaded stateMap={this.state.jobs} />
        </div>
      </div>;
    }

    var jobs = {};
    _.each(this.state.jobs, (v, k) => {
      jobs[k] = v.getReturnedData();
    });

    var source = builds[0].source;

    return [builds, jobs, source];
  },

  render: function() {
    var change_type = this.props.type;
    if ((change_type === 'diff') !== (!!this.props.diffData)) {
      return <ProgrammingError>
        diffData must be present when the type is diff (and only when)
      </ProgrammingError>;
    }

    var result = this.finishFetchingData();
    if (!_.isArray(result)) {
      return result;
    } else {
      var [builds, jobs, source] = result;
    }

    var slug = this.props.project, 
      uuid = this.props.sourceUUID;

    // Our rendering is basically a timeline: build, build, build, commit/diff_info
    // The sequence should be sorted by time started/committed...so hopefully
    // commit_info will always be the last item rendered
    var renderables = _.map(builds, b =>
      ({
        type: 'build', 
        date: b.dateCreated,
        build: b,
        jobPhases: _.pick(jobs, _.pluck(b.jobs, 'id')),
      })
    );

    switch (change_type) {
      case 'commit':
        renderables.push({
          type: 'commit', 
          date: source.revision.dateCommitted, 
          commit: source,
        });
        break;

      case 'diff':
        var diff_data = this.props.diffData;

        renderables.push({
          type: 'diff', 
          date: moment.unix(diff_data.dateCreated).toString(),
          diff: diff_data
        });

        // add renderable for every update to the diff
        var first_diff_id = _.last(diff_data.diffs);
        _.each(diff_data.diffs, single_diff_id => {
          var changes_data = diff_data.changes[single_diff_id];
          if (!changes_data) {
            this.warnings.push(
              'This diff was updated without any builds having been kicked off');
            return;
          }
          if (single_diff_id === first_diff_id) { // ignore initial diff
            return;
          }
          renderables.push({
            type: 'diff_update',
            date: moment.utc(changes_data.dateCreated),
            update: changes_data
          });
        });
        break;

      default:
        return <ProgrammingError>Unknown type {change_type}</ProgrammingError>;
    }

    renderables = _.sortBy(renderables, p => moment(p.date).unix()).reverse();

    var markup = _.map(renderables, r => {
      switch (r.type) {
        case 'commit': return this.renderCommit(r);
        case 'build': return this.renderBuild(r);
        case 'diff': return this.renderDiff(r);
        case 'diff_update': return this.renderDiffUpdate(r);
        default: console.warn('unknown renderable: ' + r.type);
      }
    });

    var sidebar_style = {
      position: 'fixed',
      top: 32,
      left: 0,
      bottom: 0,
      width: 280,
      'overflow-y': 'auto',
      'overflow-x': 'hidden',
      paddingLeft: 10,
      paddingTop: 10,
      borderRight: "1px solid #bbb",
      verticalAlign: "top"
    };

    var content_style = {
      marginLeft: 300,
    };

    // TODO: cleanup!
    // padding: "10px 35px", 
    return <ChangesPage bodyPadding={false} fixed={true}>
      <div style={sidebar_style}>
        <SideItems 
          renderables={renderables} 
          showProjectNames={!this.props.specificProject} 
        />
      </div>
      <div style={{paddingTop: 32}}>
        <div style={content_style} >
          {_.map(this.warnings, w => <Error style={{margin: 10}}>{w}</Error>)}
          {markup}
        </div>
      </div>
    </ChangesPage>;
  },

  renderBreadcrumbs: function(builds, source) {
    var change_type = this.props.type,
      diff_data = this.props.diffData;

    var this_page = '';
    if (change_type === 'diff') {
      this_page = "D" + diff_data.revision_id + ": " +
        diff_data.title + ' (' + diff_data.statusName + ')';
    } else if (change_type === 'commit') {
      this_page = source.revision.sha.substr(0,12) + ": " +
        utils.truncate(utils.first_line(source.revision.message));
    }

    if (this.props.specificProject) {
      var project = builds[0].project;
      var project_href = `/v2/project/${project.slug}`;

      var icon = <i className="fa fa-caret-right marginLeftS marginRightS" />;
      return <div style={{padding: 10}}>
        <a href={project_href}>{project.name}</a> 
        {icon}
        {this_page}
      </div>;
    }
 
    // Note: we don't know who wrote phabricator diffs (even after the freakin'
    // phabricator call!)..., otherwise author would be a good breadcrumb
    // TODO: maybe rethink breadcrumbs

    return <div style={{padding: 10}}>{this_page}</div>;
  },

  renderBuild: function(renderable) {
    // note: build.jobs contains information about the job. job_phases
    // contains lists of phases data for each job
    var build = renderable.build;
    var job_phases = renderable.jobPhases;

    // the backend may alert us that weird things happened (e.g. unable to 
    // collect a test artifact.) Show it here.
    var alerts_markup = [];
    _.each(build.failures, (f, index) => {
      // don't show the test failures reason...its already part of the normal ui
      if (f.id === 'test_failures') {
        return;
      }

      alerts_markup.push(
        <Error className={index > 0 ? 'marginTopM' : ''}>
          {f.reason}
        </Error>
      );
    });

    var build_cause = {
      'commit': 'triggered by commit',
      'diff': 'triggered by Phabricator',
      'arc test': 'triggered by arc test',
      'retry': 'triggered manually'
      // "unknown" - handled below
    }[get_build_cause(build)] || "(unknown trigger)"

    // if there are multiple projects, prefix with project name
    var project_name = '';
    if (!this.props.specificProject) {
      project_name = build.project.name + " ";
    }

    var header = this.renderHeader(
      <div>
        {project_name}
        Build
        {" #"}
        {build.number}
        {" "}{build_cause}
      </div>,
      moment.utc(build.dateFinished || build.dateStarted)
    );

    return this.renderSection(
      hash_id(build.id),
      <div>
        {header}
        {alerts_markup}
        {this.renderFailedTests(build, job_phases)}
        {this.renderJobs(build, job_phases)}
      </div>
    );
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
          utils.update_state_key('expandedTests', 
            test.id, 
            !this.state.expandedTests[test.id])
        );

        // TODO: use an instance variable to record whether we've sent the 
        // data fetch
        if (!this.state.tests[test.id]) {
          api.fetchMap(this, 'tests', {
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
        if (!api.isLoaded(this.state.tests[test.id])) {
          rows.push(GridRow.oneItem(
            <APINotLoaded 
              className="marginTopM" 
              state={this.state.tests[test.id]} 
              isInline={true} 
            />
          ));
        } else {
          var data = this.state.tests[test.id].getReturnedData();
          rows.push(GridRow.oneItem(
            <div className="marginTopM">
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
      revert_link = <a onClick={on_click}>How do I revert this?</a>;
      if (this.state.showRevertInstructions[build.id]) {
        revert_markup = <pre className="yellowPre">
          {custom_content_hook('revertInstructions')}
        </pre>;
      }
    }

    return <div id={hash_id(build.id + "_tests")}>
      {this.renderSubheader("Failed Tests", revert_link)}
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
  renderJobs: function(build, job_phases) {
    var markup = _.map(build.jobs, (j, index) => {
      var slug = build.project.slug;

      // we'll render a table with content from each phase
      var phases_rows = _.map(job_phases[j.id], (phase, index) => {
        // what the server calls a jobstep is actually a shard
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

          var links = [];

          var log_id = shard.logSources[0] && shard.logSources[0].id;
          if (log_id) {
            var old_log_uri = `/projects/${slug}/builds/${build.id}/jobs/${j.id}/logs/${log_id}/`;
            links.push(<a className="marginRightS" href={old_log_uri} target="_blank">
              Log
              <i style={{marginLeft: 3, opacity: 0.5}} className="fa fa-backward" />
            </a>);

            var raw_log_uri = `/api/0/jobs/${j.id}/logs/${log_id}/?raw=1`;
            links.push(<a className="external marginRightS" href={raw_log_uri} target="_blank">Raw</a>);
          } 
          if (shard.data.uri) {
            links.push(<a classname="external" href={shard.data.uri} target="_blank">Jenkins</a>);
          }

          return [
            index === 0 ? <b>{phase.name}</b> : "",
            <StatusDot state={shard_state} />,
            node_name,
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

      // TODO: change grid background
      var job_grid = <Grid
        colnum={5}
        className="marginTopS"
        data={_.flatten(phases_rows, true)}
        headers={job_headers}
        cellClasses={cellClasses}
      />;

      return <div>
        <div id={hash_id(j.id)} />
        {this.renderSubheader(j.name)}
        {job_grid}
      </div>;
    });

    return <div>
      {markup}
    </div>;
  },

  renderCommit: function(renderable) {
    var commit = renderable.commit;
    var commit_time = commit.revision.dateCommitted;

    var header = this.renderHeader(
      `Committed ${commit.revision.sha.substr(0,12)}`,
      moment.utc(commit_time));


    return this.renderSection(
      hash_id(commit.revision.sha),
      <div>
        {header}
        <pre className="commitMsg">
          {display_utils.linkify_urls(commit.revision.message)}
        </pre>
      </div>
    );
  },

  renderDiff: function(renderable) {
    var diff_data = renderable.diff;
    var diff_time = diff_data.dateCreated;

    var header = this.renderHeader(
      `Created ${'D' + diff_data.revision_id}`,
      moment.unix(diff_time));

    var content = [
      <pre className="yellowPre">
        Its a diff! We don't have any info...is Phabricator down?
      </pre>
    ];

    if (diff_data.summary) {
      content = [
        <pre className="yellowPre">
          {display_utils.linkify_urls(diff_data.summary)}
        </pre>
      ];
    }

    return this.renderSection(
      hash_id(diff_data.revision_id),
      <div>
        {header}
        {content}
      </div>
    );
  },

  renderDiffUpdate: function(renderable) {
    var update = renderable.update;

    var header = this.renderHeader(
      `Updated ${'D' + update.revision_id}`,
      moment(update.dateCreated));

    return this.renderSection(
      hash_id(update.diff_id),
      <div>
        {header}
      </div>
    );
  },

  renderSection: function(id, content) {
    var style = {
      borderBottom: "1px solid #d9d8d8",
      padding: "20px"
    };

    return <div style={style} id={id}>
      {content}
    </div>;
  },

  renderHeader: function(text, moment_time) {
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
  },

  renderSubheader: function(text, extra_link) {
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
});

var SideItems = React.createClass({
  
  propTypes: {
    // look at the render function of CommitPage to see the format of this
    renderables: React.PropTypes.array,
    // Show project names
    showProjectNames: React.PropTypes.bool,
  },

  render: function() {
    var renderables = this.props.renderables;
    var history_items = _.map(renderables, r => {
      switch (r.type) {
        case 'build': return this.renderBuildEntry(r);
        case 'commit': return this.renderCommitEntry(r);
        case 'diff': return this.renderDiffEntry(r);
        case 'diff_update': return this.renderDiffUpdateEntry(r);
        default: 
          return <ProgrammingError>unknown renderable {r.type}</ProgrammingError>;
      }
    });

    var header_style = {
      fontWeight: "bold", 
      textTransform: "uppercase", 
      fontSize: 12, 
      marginBottom: 5
    };

    // TODO: history hashes don't work on initial page load
    return <div>
      <div style={header_style}>
        History
      </div>
      {history_items}
      <div style={{marginTop: 20}}>
        <div style={header_style}>
          Other Actions
        </div>
        <div style={{marginLeft: 5}}>
          <a href="#" className="commitSideItem">
            Create New Build [TODO]
          </a>
        </div>
      </div>
    </div>;
  },

  renderBuildEntry: function(renderable) {
    var build = renderable.build;
    var jobs = renderable.jobPhases;

    var time_style = {
      float: 'right',
      marginRight: 10,
      color: '#333'
    };

    var project_prefix = this.props.showProjectNames ?
      build.project.name + " " :
      '';

    var main_item = <a href={hash_href(build.id)} className="commitSideItem">
      <b style={{color: get_state_color(get_build_state(build)), display: 'block'}}>
        {project_prefix}
        Build #{build.number}
        <div style={time_style}>{display_duration(build.duration / 1000)}</div>
      </b>
    </a>;

    var tests_item = null;
    if (build.testFailures.total > 0) {
      tests_item = <a href={hash_href(build.id + "_tests")} className="commitSideItem">
        <span style={{color: colors.red}}>Failed Tests: {build.testFailures.total}</span>
        <div style={time_style}>{''}</div>
      </a>;
    }

    var job_items = _.map(build.jobs, j => {
      var color = get_state_color(
        get_runnable_state(j.status.id, j.result.id));

      var style = {
        color: color
      };

      return <a href={hash_href(j.id)} className="commitSideItem">
        <span style={style}>{utils.truncate(j.name, 40)}</span>
        <div style={time_style}>{display_duration(j.duration / 1000)}</div>
      </a>;
    });

    return <div className="commitSideSection">
      {main_item}
      {tests_item}
      {job_items}
    </div>;
  },

  renderCommitEntry: function(renderable) {
    var commit = renderable.commit;

    var icon_style = {
      backgroundColor: "black",
      borderRadius: 2,
      color: "white",
      padding: "3px 3px 4px 2px",
    };

    var time_style = {
      float: 'right',
      marginRight: 10,
      color: '#333'
    };

    var icon = <i style={icon_style} className="fa fa-code" />;

    return <div className="commitSideSection">
      <a href={hash_href(commit.revision.sha)} className="commitSideItem">
        <b style={{color: colors.darkGray}}>Committed {commit.revision.sha.substr(0,12)}{"..."}</b>
        <TimeText time={commit.revision.dateCommitted} style={time_style} />
      </a>
    </div>;
  },

  renderDiffEntry: function(renderable) {
    var diff = renderable.diff;

    var icon_style = {
      backgroundColor: "black",
      borderRadius: 2,
      color: "white",
      padding: "3px 3px 4px 2px",
    };

    var time_style = {
      float: 'right',
      marginRight: 10,
      color: '#333'
    };

    var icon = <i style={icon_style} className="fa fa-terminal" />;

    return <div className="commitSideSection">
      <a href={hash_href(diff.revision_id)} className="commitSideItem">
        <b style={{color: colors.darkGray}}>Created D{diff.revision_id}</b>
        <TimeText time={diff.dateCreated} format="X" style={time_style} />
      </a>
    </div>;
  },

  renderDiffUpdateEntry: function(renderable) {
    var update = renderable.update;

    var time_style = {
      float: 'right',
      marginRight: 10,
      color: '#333'
    };

    return <div className="commitSideSection">
      <a href={hash_href(update.diff_id)} className="commitSideItem" style={{backgroundColor: colors.lightGray}}>
        <b style={{color: colors.darkGray}}>Updated D{update.revision_id}</b>
        <TimeText time={update.dateCreated} style={time_style} />
      </a>
    </div>;
  },
});

// generate # links/div ids for in-page navigation
var hash_id = function(id) { return "s_" + id; }
var hash_href = function(id) { return "#" + hash_id(id); }
