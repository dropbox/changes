import React from 'react';

import { TimeText } from 'es6!display/time';
import { StatusDot, status_dots } from 'es6!display/builds';
import Grid from 'es6!display/grid';
import NotLoaded from 'es6!display/not_loaded';
import { RandomLoadingMessage } from 'es6!display/loading';
import ChangesPage from 'es6!display/page_chrome';
import { Menu1, Menu2 } from 'es6!display/menus';

import { fetch_data } from 'es6!utils/data_fetching';
import colors from 'es6!utils/colors';

var cx = React.addons.classSet;

var ProjectPage = React.createClass({

  getInitialState: function() {
    return {
      selectedItem: 'Commits', // duplicated in componentDidMount
      projectStatus: 'loading',
      commitsStatus: 'loading',
      detailsStatus: 'loading',
      todoStatus: 'loading'
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
    fetch_data(this, {
      'project': `/api/0/projects/${slug}`,
      'commits': Commits.getDataToLoad(slug),
      'details': ProjectDetails.getDataToLoad(slug),
      'todo': '/api/0/authors/me/diffs/'
    });
  },

  render: function() {
    if (this.state['projectStatus'] !== 'loaded') {
      return <NotLoaded
        loadStatus={this.state.projectStatus}
        errorData={this.state.projectError}
      />;
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

    // TODO: rather than unmounting and remounting (causing a new data fetch),
    // just use display: none. OR, push the state up to the page component,
    // so that we can just ship it down using props (better).
    var menu = <Menu2 
      items={menu_items} 
      selectedItem={selected_item} 
      onClick={onClick}
    />;

    // grab data for currently selected section and render it
    var all_prefixes = {
      'Commits': 'commits',
      'Project Details': 'details'
    }
    var prefix = all_prefixes[this.state.selectedItem] || 'todo';

    var selectedStatus = this.state[prefix+"Status"],
      selectedData = this.state[prefix+"Data"], 
      selectedError = this.state[prefix+"Error"];

    var component = null;
    if (selectedStatus === 'loaded') {
      component = React.createElement(
        this.getComponentClassForSelection(this.state.selectedItem), 
        {data: selectedData, projectData: this.state.projectData}
      );
    } else {
      component = <NotLoaded 
        loadStatus={selectedStatus}
        errorData={selectedError}
        isInline={true}
      />;
    }

    var padding_classes = 'paddingLeftM paddingRightM';
    return <ChangesPage bodyPadding={false}>
      {this.renderProjectInfo(this.state.projectData)}
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
      data: []
    };
  },

  statics: {
    getDataToLoad: function(project_slug) {
      var endpoint = `/api/0/projects/${project_slug}/commits/?branch=master&all_builds=1`;
      return {'commits': endpoint};
    }
  },

  render: function() {
    var commits = this.props.data.commitsData;
    var project_info = this.props.projectData;

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
    var plan = this.props.data.detailsData;

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
