import React from 'react';
import moment from 'moment';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesPage from 'es6!display/page_chrome';
import SectionHeader from 'es6!display/section_header';
import { BuildWidget, status_dots_for_diff, get_runnable_state } from 'es6!display/changes/builds';
import { Grid } from 'es6!display/grid';
import { TimeText } from 'es6!display/time';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';
import colors from 'es6!utils/colors';
import custom_content_hook from 'es6!utils/custom_content';

var HomePage = React.createClass({

  getInitialState: function() {
    return {
      commits: null,
      diffs: null
    }
  },

  componentDidMount: function() {
    var author = this.props.author || 'me';

    api.fetch(this, {
      diffs: `/api/0/authors/${author}/diffs/`,
      commits: `/api/0/authors/${author}/commits/?per_page=20`,
      projects: '/api/0/projects/' // no fetch_extra
    });
  },


  render: function() {
    // NOTE: so right now, this page still basically works even when
    // phabricator is down. Keep it that way.

    // I want to display just a single loading indicator until we have content
    // to show
    if (!api.isLoaded(this.state.commits)) {
      // special rendering for not logged in
      if (api.isError(this.state.commits) &&
          this.state.commits.getStatusCode() === '401') {
        return this.renderNotLoggedIn();
      }

      return <ChangesPage highlight="My Changes" isPageLoaded={false}>
        <APINotLoaded state={this.state.commits} isInline={true} />
      </ChangesPage>;
    }

    var header_markup = null;
    if (this.props.author) {
      // hack to use homepage as user page
      // TODO: not this
      var author_info = this.state.commits.getReturnedData()[0].builds[0].author;
      header_markup = <div style={{paddingBottom: 10}}>
        User page for {author_info.name}. Right now its just a crappy copy
        of the home page...I{"'"}ll improve this soon.
      </div>;
    }

    return <ChangesPage highlight="My Changes">
      {header_markup}
      <div>
        <Diffs
          diffs={this.state.diffs}
          isSelf={!this.props.author}
        />
        <Commits
          commits={this.state.commits}
          isSelf={!this.props.author}
        />
      </div>
      <div className="marginTopL">
        <Projects
          commits={this.state.commits}
          projects={this.state.projects}
          isSelf={!this.props.author}
        />
      </div>
    </ChangesPage>;
  },

  renderNotLoggedIn: function() {
    var current_location = encodeURIComponent(window.location.href);
    var login_href = '/auth/login/?orig_url=' + current_location;

    return <ChangesPage highlight="My Changes">
      <div className="marginBottomL">
        <a href={login_href}>
          Log in
        </a>
        {" "}
        to see your recent diffs and commits.
      </div>
      <Projects projects={this.state.projects} />
    </ChangesPage>;
  }
});

// Render list of the user's diffs currently in review / uncommitted
var Diffs = React.createClass({

  propTypes: {
    // diffs authored by the user (and associated builds)
    diffs: React.PropTypes.array,

    // isSelf = false when we're using this page as a makeshift user page
    isSelf: React.PropTypes.bool
  },

  getInitialState: function() {
    return {};
  },

  render: function() {
    if (!api.isLoaded(this.props.diffs)) {
      return <APINotLoaded state={this.props.diffs} isInline={true} />;
    }

    var diffs = this.props.diffs.getReturnedData();

    var grid_data = _.map(diffs, d => {
      var ident = "D" + d.id;

      var latest_builds = null;
      if (d.builds.length > 0) {
        // TODO: nit, but if there are no builds, let's render an invisible
        // clickable widget

        // TODO: link to a summary of builds page
        var builds_href = URI(`/v2/diff/${ident}/`)
          .search({buildID: _.last(d.builds).id})
          .toString();

        latest_builds = <a className="diffBuildsWidget" href={builds_href}>
          {status_dots_for_diff(d.builds)}
        </a>;
      }

      return [
        latest_builds,
        <a className="external" href={d['uri']} target="_blank">{ident}</a>,
        d['statusName'],
        d['title'],
        <TimeText time={d['dateModified']} format="X" />
      ];
    });

    var cellClasses = ['nowrap buildWidgetCell', 'nowrap', 'nowrap', 'wide', 'nowrap'];
    var headers = [
      'Build(s)',
      'Diff',
      'Status',
      'Name',
      'Updated'
    ];

    var header_text = this.props.isSelf ?  'My Diffs' : 'Diffs';
    return <div className="paddingBottomM">
      <SectionHeader>{header_text}</SectionHeader>
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
    // commits authored by the user (and associated builds)
    commits: React.PropTypes.object,

    // isSelf = false when we're using this page as a makeshift user page
    isSelf: React.PropTypes.bool
  },

  getInitialState: function() {
    return {};
  },

  render: function() {
    if (!api.isLoaded(this.props.commits)) {
      return <APINotLoaded state={this.props.commits} isInline={true} />;
    }

    var commits = this.props.commits.getReturnedData();

    if (commits.length === 0) {
      return <div>I don{"'"}t see any commits!</div>;
    }

    var grid_data = [];
    commits.forEach(c => {
      var sha_item = c.revision.sha.substr(0,7);
      if (c.revision.external && c.revision.external.link) {
        sha_item = <a
          className="external"
          href={c.revision.external.link}
          target="_blank">
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
        // render the commit even if there are no builds for it (especially if!)
        grid_data.push(
          [
            <span style={{fontStyle: 'italic', color: colors.darkGray, marginLeft: 3}}>
              None
            </span>,
            sha_item,
            '',
            utils.truncate(utils.first_line(c.revision.message)),
            <TimeText time={c.revision.dateCommitted} />
          ]
        );
        return;
      }

      _.each(project_slugs, slug => {
        var matching_builds = _.filter(c.builds,
          b => b.project.slug === slug
        );
        var last_build = _.extend({}, matching_builds[0], {source: c});

        var project = last_build.project;

        var widget = <BuildWidget build={last_build} parentElem={this} />;

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
      'Commit',
      'Project',
      'Name',
      'Committed'
    ];

    // custom content link for a tool to show whether commits have been
    // pushed to prod
    var is_it_out_markup = null;

    var all_project_slugs = _.chain(commits)
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
        <a className="external" href={is_it_out_link} target="_blank">Is it out?</a>
        {"]"}
      </span>;
    }

    var header_text = this.props.isSelf ?
      'My Commits' : 'Commits';

    return <div className="marginTopM">
      <div className="marginBottomS">
        <SectionHeader className="inline">{header_text}</SectionHeader>
        {is_it_out_markup}
      </div>
      <Grid
        colnum={5}
        data={grid_data}
        cellClasses={cellClasses}
        headers={headers}
      />
      <br /><div>Click <a href="/v2/builds">here</a> to see your builds!</div>
    </div>;
  }
});

// List of projects. Color indicates if the latest build is green or red
var Projects = React.createClass({
  propTypes: {
    projects: React.PropTypes.object,

    // optional: we'll bold projects that the user has recently committed to
    commits: React.PropTypes.object,
  },

  render: function() {
    var projects_api = this.props.projects;

    if (!api.isLoaded(projects_api)) {
      return <APINotLoaded state={projects} isInline={true} />;
    }

    var projects = projects_api.getReturnedData();

    var commits = this.props.commits && this.props.commits.getReturnedData();

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
        switch (get_runnable_state(p.lastBuild)) {
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
        <SectionHeader className="inline">Projects</SectionHeader>
      </div>
      {project_table}
      <div className="lt-darkgray marginTopM">
        Projects that haven{"'"}t run a build in the last week
        are hidden.{" "}
        <a href="/v2/projects/">See all</a>
      </div>
    </div>;
  }
});

export default HomePage;
