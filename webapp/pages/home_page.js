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
      commitsStatus: 'loading',
      commitsData: null,
      commitsError: null,

      diffsStatus: 'loading',
      diffsData: null,
      diffsError: {},
    }
  },

  componentDidMount: function() {
    var author = this.props.author || 'me';

    // TODO: handle user not logged in
    var diffs_endpoint = `/api/0/authors/${author}/diffs/`;
    var commits_endpoint = `/api/0/authors/${author}/commits/`;

    fetch_data(this, {
      diffs: diffs_endpoint,
      commits: commits_endpoint
    });
  },

  render: function() {
    // we can't render anything until we get commit data. If we have commit data
    // but not diffs data, render as much of the page as we can.
    // TODO: its super-easy to do a partial render, but is it better to just
    // wait for everything?
    if (this.state.commitsStatus === "loading") {
      return <div><RandomLoadingMessage /></div>;
    }

    return <ChangesPage>
      {this.renderContent()}
    </ChangesPage>;
  },

  renderContent: function() {
    if (this.state.commitsStatus === "error") {
      return <AjaxError response={this.state.commitsError.response} />;
    }

    var commits = this.state.commitsData;

    if (!commits) {
      // TODO: maybe show all projects or something?
      return <div>I don{"'"}t see any commits!</div>;
    }

    var diffs = this.state.diffsStatus === "loaded" ?
      this.state.diffsData : [];

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
          diffs={diffs}
          errorResponse={this.state.diffsError.response}
        />
        <Commits commits={commits} />
      </div>
      <div>
        <Projects
          commits={commits}
        />
      </div>
    </div>;
  },
});

// Render list of the user's diffs currently in review / uncommitted
var Diffs = React.createClass({
  
  propTypes: {
    loadStatus: React.PropTypes.string,
    diffs: React.PropTypes.array
    // errorResponse
  },

  render: function() {
    if (this.props.loadStatus === 'loading') {
      return <InlineLoading className="marginBottomM" />;
    } else if (this.props.loadStatus === 'error') {
      return <AjaxError 
        className="marginBottomM" 
        response={this.props.errorResponse} 
      />;
    }

    var grid_data = _.map(this.props.diffs, d => {
      return [
        status_dots(d.builds),
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

// List of user's recent commits
var Commits = React.createClass({
  
  propTypes: {
    commits: React.PropTypes.array.isRequired,
  },

  render: function() {
    if (this.props.commits.length === 0) {
      // TODO: transfer props?
      // TODO: Show something
      return <div />;
    }

    var grid_data = [];
    this.props.commits.forEach(c => {

      // we want to render a separate row per project
      var project_slugs = _.chain(c.builds)
        .map(b => b.project.slug)
        .compact()
        .uniq()
        .value();
      
      _.each(project_slugs, slug => {
        var matching_builds = _.filter(c.builds,
          b => b.project.slug === slug
        );

        var project = matching_builds[0].project;

        var status_results = status_dots(matching_builds);

        var source_uuid = c.id;
        var sha = c.revision.sha;

        var sha_href = `/v2/project_commit/${slug}/${source_uuid}`;
        var sha_link = <a href={sha_href}>
          {sha.substr(0,5) + "..."}
        </a>;


        var project_href = "/v2/project/" + slug;
        var project_link = <a href={project_href}>
          {project.name}
        </a>;

        // TODO: do i need this? If I do, need a boundary between commits
        grid_data = grid_data.slice(0, 50);
        grid_data.push(
          [
            status_results,
            {sha_link},
            project_link,
            utils.truncate(c.revision.message.split("\n")[0]),
            <TimeText time={c.revision.dateCreated} />
          ]
        );
      });
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

    var all_project_slugs = _.chain(this.props.commits)
      .pluck('builds')
      .flatten()
      .map(b => b.project.slug) 
      .compact()
      .uniq()
      .value();

    var is_it_out_link = custom_content_hook('isItOutHref', null, all_project_slugs);
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

// List of projects. Right now, its a list of all projects the user has
// committed to
var Projects = React.createClass({
  propTypes: {
    commits: React.PropTypes.array.required,
  },

  render: function() {
    if (this.props.commits.length === 0) {
      // TODO: transfer props?
      return <div />;
    }

    var projects = _.chain(this.props.commits)
      .pluck('builds')
      .flatten()
      .pluck('project') 
      .compact()
      .uniq(false, p => p.slug)
      .value();

    var project_links = _.map(projects, p => {
      var url = "/v2/project/" + p.slug;
      return [
        <a href={url}>{p.name}</a>,
        "TODO: show build history of proj"
      ];
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

export default HomePage;
