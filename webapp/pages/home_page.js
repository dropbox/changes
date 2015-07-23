import React from 'react';

import { AjaxError } from 'es6!display/errors';
import { Grid } from 'es6!display/grid';
import { StatusDot, status_dots, BuildWidget, get_build_state } from 'es6!display/builds';
import SectionHeader from 'es6!display/section_header';
import { InlineLoading, RandomLoadingMessage } from 'es6!display/loading';
import APINotLoaded from 'es6!display/not_loaded';
import ChangesPage from 'es6!display/page_chrome';
import { TimeText } from 'es6!display/time';

import * as api from 'es6!server/api';
import colors from 'es6!utils/colors';
import custom_content_hook from 'es6!utils/custom_content';
import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

var HomePage = React.createClass({

  getInitialState: function() {
    return {
      commits: null,
      diffs: null
    }
  },

  componentDidMount: function() {
    var author = this.props.author || 'me';

    // TODO: handle user not logged in
    var diffs_endpoint = `/api/0/authors/${author}/diffs/`;
    // TODO: we may not render all 20...some commits may kick off like 4 builds
    var commits_endpoint = `/api/0/authors/${author}/commits/?per_page=20`;
    var projects_endpoint = '/api/0/projects/'; // no fetch_extra

    api.fetch(this, {
      diffs: diffs_endpoint,
      commits: commits_endpoint,
      projects: projects_endpoint,
    });
  },

  render: function() {
    // we can't render anything until we get commit data. If we have commit data
    // but not diffs data, render as much of the page as we can.
    // NOTE: so right now, this page still basically works even when
    // phabricator is down. Keep it that way.
    if (!api.isLoaded(this.state.commits) && !api.isError(this.state.commits)) {
      return <div><RandomLoadingMessage /></div>;
    }

    return <ChangesPage highlight="My Changes">
      {this.renderContent()}
    </ChangesPage>;
  },

  renderContent: function() {
    if (this.state.commits.condition === "error") {
      return <AjaxError response={this.state.commits.response} />;
    }

    var commits = this.state.commits.getReturnedData();

    if (!commits) {
      // TODO: maybe show all projects or something?
      return <div>I don{"'"}t see any commits!</div>;
    }

    var diffs = api.isLoaded(this.state.diffs) ? 
      this.state.diffs.getReturnedData() : 
      [];

    var header_markup = null;
    if (this.props.author) {
      // hack to use homepage as user page
      // TODO: not this
      var author_info = commits[0].builds[0].author; 
      header_markup = <div style={{paddingBottom: 10}}>
        User page for {author_info.name}. Right now its just a crappy copy 
        of the home page...I{"'"}ll improve this soon.
      </div>;
    }

    return <div>
      {header_markup}
      <div>
        <Diffs
          loadStatus={this.state.diffs.condition}
          diffs={diffs}
          errorResponse={this.state.diffs.response}
        />
        <Commits commits={commits} />
      </div>
      <div className="marginTopL">
        <Projects
          commits={commits}
          projects={this.state.projects}
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
      var ident = "D" + d.id;
      var href = `/v2/diff/${ident}/`;

      return [
        d.builds.length > 0 ? 
          <BuildWidget href={href} build={_.first(d.builds)} /> : 
          null,
        <a href={d['uri']} target="_blank">{ident}</a>,
        d['statusName'],
        d['title'],
        <TimeText time={d['dateModified']} format="X" />
      ];
    });

    var cellClasses = ['nowrap buildWidgetCell', 'nowrap', 'nowrap', 'wide', 'nowrap'];
    var headers = [
      'Last Build',
      'Phab.',
      'Status',
      'Name',
      'Updated'
    ];

    return <div className="paddingBottomM">
      <SectionHeader>In Review</SectionHeader>
      <Grid 
        colnum={5}
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
      // TODO: Show something
      return <div />;
    }

    var grid_data = [];
    this.props.commits.forEach(c => {

      var sha = c.revision.sha;
      var sha_item = sha.substr(0,7);
      if (c.revision.external && c.revision.external.link) {
        sha_item = <a href={c.revision.external.link} target="_blank">
          {sha_item}
        </a>;
      }

      // we want to render a separate row per project
      var project_slugs = _.chain(c.builds)
        .map(b => b.project.slug)
        .compact()
        .uniq()
        .value();
      
      if (project_slugs.length === 0) {
        grid_data.push(
          [
            <span style={{fontWeight: 'bold', fontStyle: 'italic', color: colors.darkGray, marginLeft: 3}}>
              None
            </span>,
            sha_item,
            '',
            utils.truncate(utils.first_line(c.revision.message)),
            <TimeText time={c.revision.dateCommitted} />
          ]
        );
      }

      _.each(project_slugs, slug => {
        var matching_builds = _.filter(c.builds,
          b => b.project.slug === slug
        );
        var last_build = _.extend({}, matching_builds[0], {source: c});

        var project = last_build.project;

        var widget = <BuildWidget build={last_build} />;

        var project_href = "/v2/project/" + slug;
        var project_link = <a href={project_href}>
          {last_build.project.name}
        </a>;

        grid_data.push(
          [
            widget,
            sha_item,
            project_link,
            utils.truncate(utils.first_line(c.revision.message)),
            <TimeText time={c.revision.dateCommitted} />
          ]
        );
      });
    });

    var cellClasses = ['nowrap buildWidgetCell', 'nowrap', 'nowrap', 'wide', 'nowrap'];
    var headers = [
      'Last Build',
      'Hash',
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
      is_it_out_markup = <span>
        {" ["}
        <a href={is_it_out_link} target="_blank">Is it out?</a>
        {"]"}
      </span>;
    }

    return <div className="marginTopM">
      <div className="marginBottomS">
        <SectionHeader className="inline">Commits</SectionHeader>
        {is_it_out_markup}
      </div>
      <Grid 
        colnum={5}
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
    projects: React.PropTypes.object,
    commits: React.PropTypes.array
  },

  render: function() {
    var projects_api = this.props.projects;

    if (!api.isLoaded(projects_api)) {
      return <APINotLoaded state={projects} isInline={true} />;
    }

    var projects = projects_api.getReturnedData();

    var author_projects = [];
    if (this.props.commits) {
      // grab projects recently committed to by author
      var author_projects = _.chain(this.props.commits)
        .pluck('builds')
        .flatten()
        .pluck('project')
        .compact()
        .map(p => p.slug)
        .uniq()
        .value();
    }

    var color_cls = '';
    var project_entries = _.compact(_.map(projects, p => {
      if (p.lastBuild) {
        // ignore projects over a week old
        // TODO: centralize this logic with all projects page
        var age = moment.utc().format('X') - 
          moment.utc(p.lastBuild.dateCreated).format('X');
        if (age > 60*60*24*7) { // one week
          return null;
        }
        switch (get_build_state(p.lastBuild)) {
          case 'passed':
            color_cls = 'lt-green';
            break;
          case 'failed':
          case 'nothing':
            color_cls = 'lt-red';
            break;
        }
      }

      var url = "/v2/project/" + p.slug;
      var project_name = _.contains(author_projects, p.slug) ?
        <span className="bb">{p.name}</span> :
        p.name;
      return <a className={color_cls} href={url}>{project_name}</a>;
    }));

    // render names in 3 columns
    var num_per_column = Math.ceil(project_entries.length / 3);
    var column1 = project_entries.slice(0, num_per_column);
    var column2 = project_entries.slice(num_per_column, num_per_column * 2)
    var column3 = project_entries.slice(num_per_column * 2)
    var zipped = _.zip(column1, column2, column3);

    var project_rows = _.map(zipped, items => {
      var [v1, v2, v3] = items;
      return <tr>
        <td><span className="marginRightL">{v1}</span></td>
        <td><span className="marginRightL">{v2}</span></td>
        <td>{v3}</td>
      </tr>
    });
    var project_table = <table className="invisibleTable">{project_rows}</table>;

    return <div>
      <div style={{marginBottom: 3, borderBottom: "1px solid #d9d8d8", paddingBottom: 5}}>
        <SectionHeader className="inline">Active Projects</SectionHeader>
        <span>
          {" ["}
          <a href="/v2/projects/">More Info</a>
          {"]"}
        </span>
      </div>
      {project_table}
    </div>;
  }
});

export default HomePage;
