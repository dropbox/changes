import React from 'react';

import { AjaxError } from 'es6!display/errors';
import Grid from 'es6!display/grid';
import { StatusDot, status_dots } from 'es6!display/status_indicators';
import SectionHeader from 'es6!display/section_header';
import { InlineLoading, RandomLoadingMessage } from 'es6!display/loading';
import ChangesPage from 'es6!display/page_chrome';
import { TimeText } from 'es6!display/time';

import { fetch_data } from 'es6!utils/data_fetching';
import colors from 'es6!utils/colors';
import custom_content_hook from 'es6!utils/custom_content';
import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

var HomePage = React.createClass({

  getInitialState: function() {
    return {
      buildsStatus: 'loading',
      buildsData: null,
      buildsError: null,

      diffsStatus: 'loading',
      diffsData: null,
      diffsError: {},
    }
  },

  componentDidMount: function() {
    var author = this.props.author || 'me';

    // TODO: figure out why this 404s for author != me
    // TODO: handle user not logged in
    var diffs_endpoint = `/api/0/authors/${author}/diffs/`;
    var builds_endpoint = `/api/0/authors/${author}/builds/?per_page=100`;

    fetch_data(this, {
      diffs: diffs_endpoint,
      builds: builds_endpoint
    });
  },

  render: function() {
    // we can't render anything until we get build data. If we have build data
    // but not diffs data, render as much of the page as we can.
    // TODO: its super-easy to do a partial render, but is it better to just
    // wait for everything?
    if (this.state.buildsStatus === "loading") {
      return <div><RandomLoadingMessage /></div>;
    }

    return <ChangesPage>
      {this.renderContent()}
    </ChangesPage>;
  },

  renderContent: function() {
    if (this.state.buildsStatus === "error") {
      return <AjaxError response={this.state.buildsError.response} />;
    }

    var build_list = this.state.buildsData;

    if (!build_list) {
      // TODO: maybe show all projects or something?
      return <div>I don{"'"}t see any builds!</div>;
    }

    var diffs = this.state.diffsStatus === "loaded" ?
      this.state.diffsData : [];

    var changes = DEPRECATE_ME_combine_builds_into_changes(build_list);

    var header_markup = null;
    if (this.props.author) {
      // hack to use homepage as user page
      // TODO: not this
      var author_info = changes[0].builds[0].author; 
      header_markup = <div style={{paddingBottom: 10}}>
        User page for {author_info.name}. Right now its just a crappy copy 
        of the home page...I{"'"}ll improve this soon.
      </div>;
    }

    return <div>
      {header_markup}
      <div>
        <Diffs
          loadStatus={this.state.diffsStatus}
          changes={changes}
          diffs={diffs}
          errorResponse={this.state.diffsError.response}
        />
        <Commits
          changes={changes}
        />
      </div>
      <div>
        <Projects
          changes={changes}
        />
      </div>
    </div>;
  },
});

var Diffs = React.createClass({
  
  propTypes: {
    loadStatus: React.PropTypes.string,
    changes: React.PropTypes.array,
    diffs: React.PropTypes.array
    // errorResponse
  },

  render: function() {
    if (this.props.loadStatus === 'loading') {
      return <InlineLoading className="marginBottomM" />;
    } else if (this.props.loadStatus === 'error') {
      return <AjaxError className="marginBottomM" response={this.props.errorResponse} />;
    }

    // index changes by diff id (e.g. D123511)
    var changes_by_diff_id = {};
    this.props.changes.forEach(c => {
      if (!c.isCommit) {
        // TODO: this isn't guaranteed to be consistent with every build.
        // I really need to deprecate that changes method...
        var diff_data = c.builds[0].source.data;
        if (changes_by_diff_id[diff_data["phabricator.revisionID"]]) {
          console.warn("tried to insert builds for the same change twice!");
        }
        changes_by_diff_id[diff_data["phabricator.revisionID"]] = c;
      }
    });

    var grid_data = _.map(this.props.diffs, d => {
      var change = changes_by_diff_id[d.id] || {};
      return [
        status_dots(change.builds),
        <a href={d['uri']}>{"D"+d.id}</a>,
        d['statusName'],
        d['title'],
        <TimeText time={d['dateModified']} format="X" />
      ];
    });

    var cellClasses = ['nowrap center', 'nowrap', 'nowrap', 'wide', 'nowrap'];
    var headers = [
      'Builds',
      'Diff',
      'Status',
      'Name',
      'Updated'
    ];

    return <div className="paddingBottomM">
      <SectionHeader>In Review</SectionHeader>
      <Grid 
        data={grid_data} 
        cellClasses={cellClasses} 
        headers={headers}
      />
    </div>;
  }
});

var Commits = React.createClass({
  
  propTypes: {
    changes: React.PropTypes.array.isRequired,
  },

  render: function() {
    // NOTE: This class takes different data than the commits pane on the 
    // project page. That class consumes data directly from the api (which 
    // just has builds associated with commits), this class takes "changes"

    if (this.props.changes.length === 0) {
      // TODO: transfer props?
      return <div />;
    }

    var commits = _.chain(this.props.changes)
      .filter(c => c.isCommit)
      .sortBy(c => c.commitBuild.source.revision.dateCreated)
      .value()
      .reverse();

    var grid_data = [];
    commits.forEach(c => {
      var status_results = null;
      if (c.multipleCommits) {
        status_results = <StatusDot result="weird" />;
      } else {
        status_results = status_dots(c.builds);
      }

      var source_uuid = c.commitBuild.source.id;
      var sha_href = 
        `/v2/project_commit/${c.projectSlug}/${source_uuid}`;

      var sha = c.commitBuild.source.revision.sha;
      var sha_link = <a href={sha_href}>
        {sha.substr(0,5) + "..."}
      </a>;

      var project_href = "/v2/project/" + c.projectSlug;
      var project_link = <a href={project_href}>
        {c.projectName}
      </a>;

      grid_data.push(
        [
          status_results,
          {sha_link},
          project_link,
          c.name,
          <TimeText time={c.commitBuild.source.revision.dateCreated} />
        ]
      );
    });

    var cellClasses = ['nowrap center', 'nowrap', 'nowrap', 'wide', 'nowrap'];
    var headers = [
      'Builds',
      'Commit',
      'Project',
      'Name',
      'Committed'
    ];

    // custom content link for a tool to show whether commits have been 
    // pushed to prod
    var is_it_out_markup = null;

    var project_slugs = _.chain(commits)
      .map(commits, c => c.projectSlug)
      .uniq()
      .values();
    var is_it_out_link = custom_content_hook('isItOutHref', null, project_slugs);
    if (is_it_out_link) {
      is_it_out_markup = <div style={{float: 'right'}}>
        <a href={is_it_out_link} target="_blank">Is it out?</a>
      </div>;
    }

    return <div className="marginTopM">
      {is_it_out_markup}
      <SectionHeader>Commits</SectionHeader>
      <Grid 
        data={grid_data} 
        cellClasses={cellClasses} 
        headers={headers}
      />
    </div>;
  }
});

var Projects = React.createClass({
  propTypes: {
    changes: React.PropTypes.array.required,
  },

  render: function() {
    if (this.props.changes.length === 0) {
      // TODO: transfer props?
      return <div />;
    }

    var changes_by_project = _.groupBy(this.props.changes,
      c => c.projectSlug);

    var project_links = [];
    _.chain(changes_by_project)
      .pairs()
      .sortBy(p => p[0])
      .each(pair => {
        var [slug, changes] = pair;

        var name = changes[0].projectName;
        var url = "/v2/project/" + slug;
        project_links.push(
          [<a href={url}>{name}</a>,
           "TODO: show build history of proj"]
        );
    });

    var headers = ['Name', 'Data'];
    var cellClasses = ['nowrap', 'wide'];

    return <div className="marginTopM">
      <SectionHeader>Projects</SectionHeader>
      <Grid 
        data={project_links} 
        headers={headers} 
        cellClasses={cellClasses}
      />
    </div>;
  }
});

// unify builds into individual changes. A single change will have builds 
// from its time in phabricator, as well as the final build from when its 
// committed. Changes are uniquely identified by their name and project.
// (while in phabricator, a change doesn't have the sha that commits will have)
// TODO: we have to do this server-side...most people will have too many 
// builds to send them all to the client
// TODO: this data structure might be completely unnecessary...
var DEPRECATE_ME_combine_builds_into_changes = function(build_list) {

  var changes = [];

  // searches through the changes array to see if this build is part of 
  // an existing change. -1 if its not found
  var change_get_index = (build) => {
    for (var i = 0; i < changes.length; i++) {
      if (_.first(changes[i].builds).name === build.name &&
          _.first(changes[i].builds).project.slug === build.project.slug) {
        return i;
      }
    }
    return -1;
  };

  build_list.forEach(b => {
    var i = change_get_index(b);
    if (i === -1) { // a new change we've never seen before
      changes.push({builds: [b]});
    } else {
      changes[i].builds.push(b);
    }
  });

  // fill in each change with a bunch of data before returning it
  changes.forEach(c => {
    // warn the user if it seems like we've combinged two changes into one.
    // right now we just see if we have builds for two different commit shas
    // TODO: check phabricator diffs to see if there are commits from two 
    // different parents
    var commit_shas = _.chain(c.builds)
      .filter(b => b.source.isCommit)
      .map(b => b.source.revision.sha)
      .uniq()
      .value();

    var num_commits = commit_shas.length;

    var multiple_commits = num_commits > 1;

    var commit_build = null;
    if (num_commits) {
      var commit_build = _.find(c.builds, 
        b => b.source.isCommit);
    }

    c = _.extend(c, 
      _.pick({
        name: c.builds[0].name,
        projectSlug: c.builds[0].project.slug,
        projectName: c.builds[0].project.name,
        // TODO: if this is false, _.pick doesn't add it. nbd, but...
        isCommit: num_commits > 0,
        commitBuild: commit_build,
        multipleCommits: num_commits > 1, // if true, name/proj key wasn't unique
        // builds: [...]
      }, _.identity)
    );
  }); // end changes.forEach(c =>

  return changes;
}

export default HomePage;
