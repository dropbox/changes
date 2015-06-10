import React from 'react';
import moment from 'moment';

import { ChangesPage, ChangesPageHeader } from 'es6!components/page_chrome';
import { fetch_data } from 'es6!utils/data_fetching';
import NotLoaded from 'es6!components/not_loaded';
import * as utils from 'es6!utils/utils';

import { TimeText, display_duration } from 'es6!components/time';
import { StatusDot } from 'es6!components/status_indicators';
import Grid from 'es6!components/grid';
import SectionHeader from 'es6!components/section_header';
import { Menu1, Menu2 } from 'es6!components/menus';
import colors from 'es6!utils/colors';

var cx = React.addons.classSet;

var CommitPage = React.createClass({

  getInitialState: function() {
    return {
      commitbuildsStatus: 'loading',
      commitbuildsData: null,
      commitbuildsError: null,

      buildsStatus: 'loading',
      buildsData: null,
      buildsError: null,

      jobsStatus: 'loading',
      jobsData: null,
      jobsError: null,
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
    fetch_data(this, {
      commitbuilds: endpoint
    });
  },

  render: function() {
    var slug = this.props.project, 
      uuid = this.props.sourceUUID;

    if (this.state.commitbuildsStatus !== 'loaded') {
      return <NotLoaded 
        loadStatus={this.state.commitbuildsStatus}
        errorData={this.state.commitbuildsError}
      />;
    }

    var build_ids = _.map(this.state.commitbuildsData, b => b.id);

    // hey, we need to do more data fetching. One call per build, then one 
    // call per job (!) Joy.
    // TODO: combine this all into one server-side api call

    // the process of data fetching doesn't influence rendering, so using 
    // instance variables instead of state

    if (!this.fetchedBuilds) {
      var endpoint_map = {};
      _.each(build_ids, id => {
        endpoint_map[id] = `/api/0/builds/${id}`;
      });
      fetch_data(this, {
        'builds': endpoint_map
      });

      this.fetchedBuilds = true;
    }

    if (this.state.buildsStatus !== 'loaded') {
      return <div>
        (1/3){" "}
        <NotLoaded 
          className="inline"
          loadStatus={this.state.buildsStatus}
          errorData={this.state.buildsError}
        />
      </div>;
    }
      
    var builds = [];
    _.each(this.state.buildsData, (v, k) => {
      if (k.substr(-4) === 'Data') {
        builds.push(v);
      }
    });

    // alright, we have a list of builds. Now for jobs.

    if (!this.fetchedJobs) {
      var endpoint_map = {};
      _.each(builds, b => {
        _.each(b.jobs, j => {
          endpoint_map[j.id] = `/api/0/jobs/${j.id}/phases`;
        });
      });

      fetch_data(this, {
        'jobs': endpoint_map
      });

      this.fetchedJobs = true;
    }

    if (this.state.jobsStatus !== 'loaded') {
      return <div>
        (2/3){" "}
        <NotLoaded 
          className="inline"
          loadStatus={this.state.jobsStatus}
          errorData={this.state.jobsStatus}
        />
      </div>;
    }

    var jobs = {};
    _.each(this.state.jobsData, (v, k) => {
      if (k.substr(-4) === 'Data') {
        var job_id = k.substr(0, k.length - 4);
        jobs[job_id] = v;
      }
    });

    var source = builds[0].source;
    
    // Our rendering is basically a timeline: build, build, build, commit_info
    // The sequence should be sorted by time started/committed...so hopefully
    // commit_info will always be the last item rendered
    // TODO: that revision dateCreated field better be the date the revision was
    // created and not the date the db row about the revision was created...
    var renderables = _.map(builds, b =>
      ({
        type: 'build', 
        date: b.dateCreated,
        data: b
      })
    );

    renderables.push({
      type: 'commit', 
      date: source.revision.dateCreated, 
      data: source
    });

    // TODO: not needed right now, but I really want a dateCreated data field
    // for phabricator diff sources...

    renderables = _.sortBy(renderables, p => p.date).reverse();

    var markup = _.map(renderables, r => {
      if (r.type === 'commit') {
        return this.renderCommit(r.data);
      } else if (r.type === 'build') {
        return this.renderBuild(r.data, jobs);
      } else {
        console.warn('unknown renderable: ' + r.type);
      }
    });

    // render a gray header
    var commit_title = source.revision.message.split("\n")[0];
    var commit_author = utils.email_localpart(
      source.revision.author.email);

    var project_href = `/experimental/project/${builds[0].project.slug}`;

    var header_style = {
      padding: 10,
      backgroundColor: colors.lightestGray,
      marginBottom: 10
    };


    var icon = <i className="fa fa-caret-right marginLeftS marginRightS" />;

    return <ChangesPage bodyPadding={false}>
      <ChangesPageHeader />
      <div>
        <div style={header_style}>
          <div className="marginBottomM">
            <a href={project_href}>{builds[0].project.name}</a> 
            {icon}
            Commit {source.revision.sha.substr(0,12)}
            {" "}
            (<a href={`/projects/${slug}/sources/${uuid}`}>old ui</a>)
          </div>
          <div><b>{commit_title} ({commit_author})</b></div>
        </div>
        <div className="paddingRightM">
          <div className="marginLeftM marginBottomM">
            <a href="#">Create new build [TODO]</a>
          </div>
          {markup}
        </div>
      </div>
    </ChangesPage>;
  },

  renderBuild: function(build, job_data) {
    // possible results: unknown, aborted, passed, skipped, failed, infra_failed
    // possible statuses: unknown, queued, in_progress, finished
    // TODO: handle not-yet-completed

    // brief sentences at top about what's going on.
    // Ex: Build #57 ran two jobs in 12m3s. 1 job failed: windows.
    var intro_sentence = '';
    if (build.status.id === 'finished') {
      intro_sentence = `
        Build #${build.number} 
        ran
        ${build.jobs.length} 
        ${build.jobs.length === 1 ? "job" : "jobs"}
        and
        ${build.stats.test_count}
        ${build.stats.test_count === 1 ? "test" : "tests"}
        in 
        ${display_duration(build.duration/1000)}`;
    } else if (build.status.id === 'in_progress' || 
               build.status.id === "queued") {
      intro_sentence = `
        Build #${build.number} 
        ${build.status.id === 'in_progress' ? 'is running' : 'will run'}
        ${build.jobs.length} 
        ${build.jobs.length === 1 ? "job" : "jobs"}`;
    } else {
      intro_sentence = `unknown status ${build.status.id}`;
    }
    intro_sentence = intro_sentence.trim();

    var failure_sentence = '';
    if (build.result.id === 'failed') {
      var failed_jobs = _.filter(build.jobs, j => (j.result.id === 'failed'));

      failure_sentence = `. 
        ${failed_jobs.length} 
        ${failed_jobs.length > 1 ? 'jobs' : 'job'} 
        failed:
        ${_.pluck(failed_jobs, 'name').join(", ")}
      `;
    }
    failure_sentence = failure_sentence.trim();

    // the backend may alert us that weird things happened (e.g. unable to 
    // collect a test artifact.) Show it here.

    var alerts_markup = [];
    _.each(build.failures, f => {
      // don't show the test failures reason...its already part of the normal ui
      if (f.id === 'test_failures') {
        return;
      }

      var icon_classes = "fa fa-exclamation-triangle lt-magenta";

      alerts_markup.push(
        <div>
          <span className={icon_classes} />
          {f.reason}
        </div>
      );
    });

    return this.renderItem(
      <StatusDot result={build.result.id} size="big" />,
      moment(build.dateFinished || build.dateStarted).format('llll'),
      <div>
        <div>
          {intro_sentence}
          {failure_sentence}
        </div>
        {alerts_markup}
        {this.renderFailedTests(build, job_data)}
        {this.renderBuildWork(build, job_data)}
      </div>
    );
  },

  // which tests caused the build to fail?
  renderFailedTests: function(build, job_data) {
    if (build.testFailures.total <= 0) {
      return null;
    }

    var rows = _.map(build.testFailures.tests, test => {
      var simple_name = _.last(test.name.split("."));
      return [
        <a href="$">History</a>,
        simple_name,
        test.name
      ]
    });

    return <div>
      <SectionHeader className="marginBottomS marginTopS">
        Failed Tests
      </SectionHeader>
      <Grid 
        className="lightweight marginBottomM" 
        data={rows} 
        headers={['Links', 'Name', 'Path']} 
      />
    </div>;
  },

  // what did the build actually do?
  renderBuildWork: function(build, job_data) {
    var markup = [];

    build.jobs.forEach((j, index) => {
      // TODO: add status === finished check
      var icon_classes = cx({
        'fa': true,
        'marginRightS': true,
        'fa-check-circle': j.result.id === "passed",
        'lt-green': j.result.id === "passed",
        'fa-minus-circle': j.result.id === "failed",
        'lt-red': j.result.id === "failed",
        'fa-minus-circle': j.result.id === "failed",
        'fa-clock-o': j['status'].id === "in_progress"
      });

      var desc = null;
      if (j.status.id === 'finished') {
        var test_passes = j.stats.test_count - j.stats.test_failures;
        var duration = display_duration(j.stats.test_duration/1000);

        desc = `(${test_passes}/${j.stats.test_count} in ${duration})`;
      }

      var phases_markup = _.map(job_data[j.id], phase => {
        // using the name "shard" for steps, since its a more accurate name
        var shards_markup = _.map(phase.steps, shard => {
          var log_id = shard.logSources[0].id;
          var raw_log_uri = `/api/0/jobs/${j.id}/logs/${log_id}`;

          // TODO: use the contents of the data array
          return <span className="shardRow">
            <span className="shardNode">
              {shard.node.name}
            </span>
            <span className="shardDuration">
              {display_duration(shard.duration/1000)}
            </span>
            <span className="shardLinks">
              <a href={raw_log_uri}>log</a>
            </span>
          </span>;
        });

        var header_row = null;
        if (index === 0) {
          header_row = <span className="phaseRow phaseRowHeader">
            <span className="phaseName">
            </span>
            <span className="phaseDuration">
              Duration
            </span>
            <span className="phaseLogLinks">
              Links
            </span>
          </span>;
        }

        return <div>
          {header_row}
          <span className="phaseRow">
            <span className="phaseName">
              {phase.name}
            </span>
            <span className="phaseDuration">
              {display_duration(phase.duration/1000)}
            </span>
            <span className="phaseLogLinks">
            </span>
          </span>
          {shards_markup}
        </div>;
      });

      markup.push(
        <div>
          <div className="marginBottomS">
            <span className={icon_classes} />
            {j.name}
            {" "}
            {desc}
          </div>
          <div>{phases_markup}</div>
        </div>
      );
    });

    return <div>
      <SectionHeader className="marginBottomS marginTopS">
        Build Details
      </SectionHeader>
      {markup}
    </div>;
  },

  renderCommit: function(commit) {
    var commit_time = commit.revision.dateCreated;

    var icon_style = {
      backgroundColor: "black",
      borderRadius: 2,
      color: "white",
      padding: "3px 3px 4px 2px",
    };

    return this.renderItem(
      <i style={icon_style} className="fa fa-code fa-2x" />,
      moment(commit_time).format('llll'),
      <div>
        <div>
          <b>Committed {commit.revision.sha.substr(0,12)}</b>
        </div>
        <pre className="commitMsg">
          {commit.revision.message}
        </pre>
      </div>
    );
  },

  renderItem: function(icon, timetext, content) {
    return <div className="eventWrap">
      <div className="eventTimestamp">
        {timetext}
      </div>
      <div className="event">
        <div className="eventIcon">
          {icon}
        </div>
        <div className="eventContent">
          {content}
        </div>
      </div>
    </div>;
  }
});

export default CommitPage;
