import React from 'react';

import { TimeText } from 'es6!display/time';
import { StatusDot, status_dots } from 'es6!display/builds';
import Grid from 'es6!display/grid';
import APINotLoaded from 'es6!display/not_loaded';
import { RandomLoadingMessage } from 'es6!display/loading';
import ChangesPage from 'es6!display/page_chrome';
import { Menu1, Menu2 } from 'es6!display/menus';

import * as api from 'es6!server/api';
import colors from 'es6!utils/colors';

var cx = React.addons.classSet;

var ProjectPage = React.createClass({

  getInitialState: function() {
    return {
      selectedItem: 'Commits', // duplicated in componentDidMount
      project: null,
      commits: null,
      details: null,
      todo: null
    }
  },

  getComponentClassForSelection: function(selected_item) {
    if (selected_item === 'Commits') {
      return Commits;
    } else if (selected_item === 'Project Details') {
      return ProjectDetails;
    } else {
      return TODO;
    }
  },

  componentDidMount: function() {
    var slug = this.props.project;

    // we'll just grab everything in parallel now. Its easy enough to later
    // switch this to trigger on menu click
    api.fetch(this, {
      'project': `/api/0/projects/${slug}`,
      'todo': '/api/0/authors/me/diffs/'
    });

    api.fetchMap(this, 'commits', Commits.getDataToLoad(slug));
    api.fetchMap(this, 'details', ProjectDetails.getDataToLoad(slug));
  },

  render: function() {
    if (!api.isLoaded(this.state.project)) {
      return <APINotLoaded state={this.state.projects} />;
    }

    // render menu
    var menu_items = [
      'Commits', 'Every Build', 'Tests', 'Project Details'
    ];
    var selected_item = this.state.selectedItem;

    var onClick = (item => {
      // if you try reclicking on a section again, react won't 
      // call componentWillMount a second time. So let's just do nothing.
      // TODO: maybe delete
      if (item === selected_item) {
        return;
      }

      this.setState({
        selectedItem: item
      });
    });

    var menu = <Menu2 
      items={menu_items} 
      selectedItem={selected_item} 
      onClick={onClick}
    />;

    // grab data for currently selected section and render it
    var data_keys = {
      'Commits': 'commits',
      'Project Details': 'details'
    }
    var selected_data_key = data_keys[this.state.selectedItem] || 'todo';
    var selected_data = this.state[selected_data_key];

    var component = null;
    var data_to_load = this.getComponentClassForSelection(this.state.selectedItem)
      .getDataToLoad();
    if (api.mapIsLoaded(selected_data, _.keys(data_to_load))) {
      component = React.createElement(
        this.getComponentClassForSelection(this.state.selectedItem), 
        {data: selected_data, projectData: this.state.project}
      );
    } else {
      component = <APINotLoaded 
        state={selected_data}
        isInline={true}
      />;
    }

    var padding_classes = 'paddingLeftM paddingRightM';
    return <ChangesPage bodyPadding={false}>
      {this.renderProjectInfo(this.state.project.getReturnedData())}
      <div className={padding_classes}>
        {menu}
        {component}
      </div>
    </ChangesPage>;
  },

  renderProjectInfo: function(project_info) {
    var style = {
      padding: 10,
      backgroundColor: colors.lightestGray
    };

    return <div style={style}>
      <div><b>{project_info.name}</b></div>
      <div>Repository: TODO (every commit)</div>
      <div>Build Plans: Something w/ snapshots (see details)</div>
    </div>;
  }
});

var Commits = React.createClass({

  getDefaultProps: function() {
    return {
      data: {}
    };
  },

  statics: {
    getDataToLoad: function(project_slug) {
      var endpoint = `/api/0/projects/${project_slug}/commits/?branch=master&all_builds=1`;
      return {'commits': endpoint};
    }
  },

  render: function() {
    console.log(this.props);
    var commits = this.props.data.commits.getReturnedData();
    var project_info = this.props.projectData.getReturnedData();

    return <div>
      {this.renderTableControls()}
      {this.renderTable(commits, project_info)}
    </div>;
  },

  renderTableControls: function() {
      /*
      <span className="paddingLeftS">
        Showing most recent diffs since 0:00pm
      </span>
      */
    return <div style={{marginBottom: 5, marginTop: 10}}>
      <input 
        disabled={true}
        placeholder="Search by name or SHA"
        style={{minWidth: 170, marginRight: 5}}
      />
      <select disabled={true}>
        <option value="master">Branch: Master</option>
      </select>
      <label style={{float: 'right', paddingTop: 3}}>
        <span style={/* disabled color */ {color: '#aaa', fontSize: 'small'}}>
          Live update
          <input
            type="checkbox" 
            checked={false}
            className="noRightMargin"
            disabled={true}
          />
        </span>
      </label>
    </div>;
  },

  renderTable: function(commits, project_info) {
    var grid_data = _.map(commits, c => 
      this.turnIntoRow(c, project_info)
    );

    var cellClasses = ['nowrap center', 'nowrap', 'nowrap', 'wide', 'nowrap'];
    var headers = ['Build', 'Author', 'Commit', 'Name', 'Committed'];

    return <Grid
      data={grid_data}
      cellClasses={cellClasses}
      headers={headers}
    />;
  },

  turnIntoRow: function(c, project_info) {
    var sha_abbr = c.sha.substr(0,5) + '...';
    var message_lines = c.message.split("\n");
    var title = message_lines[0];

    // TODO: we want every build associated with a commit, not just one

    var build_dots = null;
    if (c.builds && c.builds.length > 0) {
      build_dots = status_dots(c.builds);
    }

    var author = 'unknown', author_page = null;
    var author_email = c.author && c.author.email;
    if (author_email) {
      author = author_email.substring(0, author_email.indexOf('@'));
      author_page = `/v2/author/${c.author.email}`;
    }

    // TODO: just first n characters of sha?
    var commit_page = null;

    if (c.builds && c.builds.length > 0) {
      var commit_page = '/v2/project_commit/' +
        project_info.slug + '/' +
        c.builds[0].source.id;
    }

    // TODO: if there are any comments, show a comment icon on the right
    return [
      build_dots,
      author_page ? <a href={author_page}>{author}</a> : author,
      commit_page ? <a href={commit_page}>{sha_abbr}</a> : sha_abbr,
      title,
      <TimeText time={c.dateCreated} />
    ];
  }
});

var TODO = React.createClass({
  render: function() {
    return <div>TODO</div>;
  }
});

var ProjectDetails = React.createClass({

  statics: {
    getDataToLoad: function(project_slug) {
      return {
        'details': `/api/0/projects/${project_slug}/plans/`
      };
    }
  },

  render: function() {
    var plan = this.props.data.details;

    var markup = _.map(plan, p =>
      <div>
        <b>{p.name}</b><br />
        Type: {!_.isEmpty(p.steps) && p.steps[0].name}<br />
        Build Parameters:
        <pre>{!_.isEmpty(p.steps) && p.steps[0].data}</pre>
      </div>
    );

    var count_text = markup.length === 1 ?
      'One build plan' : `${markup.length} build plans`;

    return <div>
      Some more summary info will go here.
      <div>{count_text}</div>
      {markup}
    </div>;

    /*
      <!-- If just one, inline. Otherwise, one per line -->
      <!-- stats -->
      <!-- or add a stats section... --> !!!
      */
  }
});

export default ProjectPage;
