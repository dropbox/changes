import React from 'react';
import moment from 'moment';

import ChangesPage from 'es6!display/page_chrome';
import * as api from 'es6!server/api';
import APINotLoaded from 'es6!display/not_loaded';
import * as utils from 'es6!utils/utils';

import { TimeText, display_duration } from 'es6!display/time';
import { StatusDot, get_build_state, get_build_state_color, get_build_cause } from 'es6!display/builds';
import { Error } from 'es6!display/errors';
import Grid from 'es6!display/grid';
import SectionHeader from 'es6!display/section_header';
import { Menu1, Menu2 } from 'es6!display/menus';
import colors from 'es6!utils/colors';

var cx = React.addons.classSet;

/**
 * Page that shows the builds associated with a single commit within a project
 * (since multiple projects can share a repository, they would each have their
 * own version of this page)
 */
var CommitPage = React.createClass({

  getInitialState: function() {
    return {
      commitBuilds: null,
      builds: {},
      jobs: {},
    }
  },

  componentDidMount: function() {
    var slug = this.props.project;
    var uuid = this.props.sourceUUID;

    var endpoint = `/api/0/projects/${slug}/sources/${uuid}/builds`;

    this.fetchedBuilds = false;
    this.fetchedJobs = false;

    // This gets all the builds associated with a commit. But it doesn't give
    // us enough data, so we'll have to fetch individual data per build later...
    api.fetch(this, {
      commitBuilds: endpoint
    });
  },

  finishFetchingData: function() {
    // Hey, we need to do more data fetching. One call per build, then one 
    // call per job (!) Joy. Called from render(), returns either a react 
    // component (loading message) or the fetched data
    // TODO: combine this all into one server-side api call

    // We're using instance variables here to ensure we dispatch these api
    // fetches exactly once. Its a rare but legitimate use of them.

    var slug = this.props.project, 
      uuid = this.props.sourceUUID;

    if (!api.isLoaded(this.state.commitBuilds)) {
      return <APINotLoaded state={this.state.commitBuilds} />;
    }

    var build_ids = _.map(this.state.commitBuilds.getReturnedData(), b => b.id);

    // Fetch more information about each build

    if (!this.fetchedBuilds) {
      var endpoint_map = {};
      _.each(build_ids, id => {
        endpoint_map[id] = `/api/0/builds/${id}`;
      });
      api.asyncFetchMap(this, 'builds', endpoint_map);

      this.fetchedBuilds = true;
    }

    if (!api.mapIsLoaded(this.state.builds, build_ids)) {
      return <div>
        (1/3){" "}
        <APINotLoaded stateMap={this.state.builds} />
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

      api.asyncFetchMap(this, 'jobs', endpoint_map);

      this.fetchedJobs = true;
    }

    if (!api.mapIsLoaded(this.state.jobs, job_ids)) {
      return <div>
        (2/3){" "}
        <APINotLoaded stateMap={this.state.jobs} />
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
    var result = this.finishFetchingData();
    if (!_.isArray(result)) {
      return result;
    } else {
      var [builds, jobs, source] = result;
    }

    var slug = this.props.project, 
      uuid = this.props.sourceUUID;

    // Our rendering is basically a timeline: build, build, build, commit_info
    // The sequence should be sorted by time started/committed...so hopefully
    // commit_info will always be the last item rendered
    // TODO: that revision dateCreated field better be the date the revision was
    // created and not the date the db row about the revision was created...
    var renderables = _.map(builds, b =>
      ({
        type: 'build', 
        date: b.dateCreated,
        build: b,
        jobPhases: _.pick(jobs, _.pluck(b.jobs, 'id')),
        id: "s_" + b.id
      })
    );

    renderables.push({
      type: 'commit', 
      date: source.revision.dateCreated, 
      commit: source,
      id: "s_" + source.revision.sha
    });

    // TODO: not needed yet, but I really want a dateCreated data field
    // for phabricator diff sources...

    renderables = _.sortBy(renderables, p => p.date).reverse();

    var markup = _.map(renderables, r => {
      switch (r.type) {
        case 'commit': return this.renderCommit(r);
        case 'build': return this.renderBuild(r);
        default: console.warn('unknown renderable: ' + r.type);
      }
    });

    markup = _.map(markup, m => this.renderSection(m));

    var breadcrumbs = this.renderBreadcrumbs(source, builds[0].project);

    // TODO: cleanup!
    // padding: "10px 35px", 
    return <ChangesPage bodyPadding={false}>
      <div>
        {breadcrumbs}
        <div>
          <div style={{display: 'table', borderTop: "1px solid #bbb", width: "100%"}}>
            <div style={{display: 'table-cell', width: 240, minWidth: 240, paddingLeft: 10, paddingTop: 10, borderRight: "1px solid #bbb", verticalAlign: "top"}}>
              <SideItems renderables={renderables} />
            </div>
            <div style={{display: 'table-cell', verticalAlign: "top", lineHeight: "19px"}} >
              {markup}
            </div>
          </div>
        </div>
      </div>
    </ChangesPage>;
  },

  renderBreadcrumbs: function(source, project) {
    var commit_title = source.revision.message.split("\n")[0];
    var commit_author = utils.email_head(
      source.revision.author.email);

    var project_href = `/v2/project/${project.slug}`;

    var icon = <i className="fa fa-caret-right marginLeftS marginRightS" />;
    return <div style={{padding: 10}}>
      <div>
        <a href={project_href}>{project.name}</a> 
        {icon}
        {source.revision.sha.substr(0,12)}
        {": "}
        {utils.truncate(commit_title)}
      </div>
    </div>;
  },

  renderBuild: function(renderable) {
    // note: build.jobs contains information about the job. job_phases
    // contains lists of phases data for each job
    var build = renderable.build;
    var job_phases = renderable.jobPhases;

    // the backend may alert us that weird things happened (e.g. unable to 
    // collect a test artifact.) Show it here.
    var alerts_markup = [];
    _.each(build.failures, f => {
      // don't show the test failures reason...its already part of the normal ui
      if (f.id === 'test_failures') {
        return;
      }

      alerts_markup.push(
        <Error>
          {f.reason}
        </Error>
      );
    });

    // TODO: write code to figure out how a build was kicked off
    var build_cause= {
      // TODO: "autocommit": "Build automatically triggered"
      // TODO: "manual": "Build kicked off by " + build.author
      // "unknown" - handled below
    }[get_build_cause(build)] || " (unknown trigger)"

    var header = this.renderHeader(
      <div>
        Build
        {" #"}
        {build.number}
        {build_cause}
      </div>,
      moment.utc(build.dateFinished || build.dateStarted)
    );

    return this.renderSection2(
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

    var rows = _.map(build.testFailures.tests, test => {
      var simple_name = _.last(test.name.split("."));
      var href = `/v2/project_test/${test.project.id}/${test.hash}`;

      return [
        <a href={href}>History</a>,
        simple_name,
        test.name
      ]
    });

    return <div>
      {this.renderSubheader("Failed Tests")}
      <Grid 
        className="marginBottomM" 
        data={rows} 
        headers={['Links', 'Name', 'Path']} 
      />
    </div>;
  },

  // what did the build actually do?
  renderJobs: function(build, job_phases) {
    var markup = _.map(build.jobs, (j, index) => {

      // we'll render a table with content from each phase
      var phases_rows = _.map(job_phases[j.id], (phase, index) => {
        // what the server calls a jobstep is actually a shard
        return _.map(phase.steps, (shard, index) => {
          var log_id = shard.logSources[0].id;
          var raw_log_uri = `/api/0/jobs/${j.id}/logs/${log_id}/?raw=1`;

          return [
            index === 0 ? <b>{phase.name}</b> : "",
            <StatusDot state={shard.result.id} />,
            shard.node.name,
            <a href={raw_log_uri} target="_blank">Log</a>,
            display_duration(shard.duration/1000)
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
    var commit_time = commit.revision.dateCreated;

    var icon_style = {
      backgroundColor: "black",
      borderRadius: 2,
      color: "white",
      padding: "3px 3px 4px 2px",
    };

    var header = this.renderHeader(
      `Committed ${commit.revision.sha.substr(0,12)}`,
      moment(commit_time));

    return this.renderSection2(
      hash_id(commit.revision.sha),
      <div>
        {header}
        <pre className="commitMsg">
          {commit.revision.message}
        </pre>
      </div>
    );
  },

  renderSection: function(content) {
    var style = {
      borderBottom: "1px solid #d9d8d8",
      padding: "20px"
    };

    return <div style={style}>
      {content}
    </div>;
  },

  renderSection2: function(id, content) {
    return <div id={id}>
      <div>
        {content}
      </div>
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

    // TODO: cleanup
    return <div>
      <div style={header_style}>
        <div style={header_text_style}>{text}</div>
      </div>
      <div style={time_style}>
        {moment_time.format('llll')}
        {" ("}
        {moment_time.fromNow()}
        {")"}
      </div>
    </div>;
  },

  renderSubheader: function(text) {
    var style = {
      fontSize: 18,
      fontWeight: "bold",
      marginTop: 10
    };

    return <div style={style}>
      {text}
    </div>;
  }
});

var SideItems = React.createClass({
  
  propTypes: {
    // look at the render function of CommitPage to see the format of this
    renderables: React.PropTypes.array,
  },

  render: function() {
    var renderables = this.props.renderables;
    var history_items = _.map(renderables, r => {
      switch (r.type) {
        case 'build': return this.renderBuildEntry(r);
        case 'commit': return this.renderCommitEntry(r);
        default: console.warn('unknown renderable: ' + r.type);
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

    var main_item = <a href={hash_href(build.id)} className="commitSideItem">
      <b style={{color: get_build_state_color(build), display: 'block'}}>
        Build #{build.number}
        <div style={time_style}>{display_duration(build.duration / 1000)}</div>
      </b>
    </a>;

    var job_items = _.map(build.jobs, j => {
      var color = {
        'passed': colors.green,
        'failed': colors.red,
      }[j.result.id] || '#ccc';

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

    var icon = <i style={icon_style} className="fa fa-code" />;

    return <div className="commitSideSection">
      <a href={hash_href(commit.revision.sha)} className="commitSideItem">
        <b style={{color: colors.darkGray}}>Committed {commit.revision.sha.substr(0,12)}{"..."}</b>
      </a>
    </div>;
  },
});

// generate # links/div ids for in-page navigation
var hash_id = function(id) { return "s_" + id; }
var hash_href = function(id) { return "#" + hash_id(id); }

export default CommitPage;
