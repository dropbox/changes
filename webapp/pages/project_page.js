import React from 'react';

import { TimeText } from 'es6!display/time';
import { StatusDot, status_dots, BuildWidget } from 'es6!display/builds';
import Grid from 'es6!display/grid';
import { ProgrammingError } from 'es6!display/errors';
import APINotLoaded from 'es6!display/not_loaded';
import { RandomLoadingMessage } from 'es6!display/loading';
import ChangesPage from 'es6!display/page_chrome';
import { Menu1, Menu2 } from 'es6!display/menus';

import * as api from 'es6!server/api';
import * as utils from 'es6!utils/utils';
import colors from 'es6!utils/colors';

var cx = React.addons.classSet;

var ProjectPage = React.createClass({

  getInitialState: function() {
    return {
      selectedItem: 'Commits', // duplicated in componentDidMount
      project: null,
      commits: null,
      details: null,

      // Keep the state for the commit tab here (and send it via props.) This
      // preserves the state if the user clicks to another tab
      commitsState: {}
    }
  },

  componentDidMount: function() {
    var slug = this.props.project;

    // we'll just grab everything in parallel now. Its easy enough to later
    // switch this to trigger on menu click
    api.fetch(this, {
      'project': `/api/0/projects/${slug}`,
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
      'Commits', 'Tests', 'Project Details'
    ];
    var selected_item = this.state.selectedItem;

    var onClick = (item => {
      // if you try reclicking on a section again, react won't 
      // call componentWillMount a second time. So let's just do nothing.
      if (item === selected_item) {
        return;
      }
      this.setState({ selectedItem: item });
    });

    var menu = <Menu2 
      items={menu_items} 
      selectedItem={selected_item} 
      onClick={onClick}
    />;

    var content = null;
    switch (selected_item) {
      case 'Commits':
        content = <Commits
          project={this.state.project}
          data={this.state.commits}
          commitsState={this.state.commitsState}
          page={this}
        />;
        break;
      case 'Tests':
        content = <div>TODO</div>;
        break;
      case 'Project Details':
        content = <ProjectDetails
          project={this.state.project}
          data={this.state.details}
        />;
        break;
      default:
        content = <ProgrammingError>
          Unknown tab {selected_item}
        </ProgrammingError>;
    }

    var padding_classes = 'paddingLeftM paddingRightM';
    return <ChangesPage bodyPadding={false}>
      {this.renderProjectInfo(this.state.project.getReturnedData())}
      <div className={padding_classes}>
        {menu}
        {content}
      </div>
    </ChangesPage>;
  },

  renderProjectInfo: function(project_info) {
    var style = {
      padding: 10,
      backgroundColor: colors.lightestGray
    };

    var triggers = _.compact([
      project_info.options["phabricator.diff-trigger"] ? "Diffs" : null,
      project_info.options["build.commit-trigger"] ? "Commits" : null,
    ]);

    var branches_option = project_info.options["build.branch-names"];
    if (branches_option === "*") {
      var branches = "all branches";
    } else if (branches_option.split(" ").length === 1) {
      var branches = `only on ${branches_option} branch`;
    } else {
      var branches = "branches: " + branches_option.replace(/ /g, ", ");
    }

    var whitelist_msg = "";
    var whitelist_option = project_info.options["build.file-whitelist"];
    if (whitelist_option) {
      var whitelist_paths = utils.split_lines(whitelist_option);
      whitelist_msg = <b>
        Builds are only run for changes that touch 
        {" "}
        <span style={{borderBottom: "2px dotted #ccc"}}>
          certain paths
        </span>
        {"."}
      </b>
    }

    return <div style={style}>
      <div><span style={{fontWeight: 900}}>{project_info.name}</span></div>
      <b>Repository:</b>
        {" "}{project_info.repository.url}{" "}
        {" ("}
        {branches}
        {")"}
      <div>{whitelist_msg}</div>
    </div>;
  }
});

var Commits = React.createClass({

  propTypes: {
    // the data fetch specified in getDataToLoad()
    data: React.PropTypes.object,
    // the project api response
    project: React.PropTypes.object,
    commitsState: React.PropTypes.object,
    page: React.PropTypes.element.isRequired,
  },

  statics: {
    getDataToLoad: function(project_slug) {
      var endpoint = `/api/0/projects/${project_slug}/commits/?branch=master&all_builds=1`;
      return {'commits': endpoint};
    }
  },

  render: function() {
    // state is handled by parent so that its preserved on tab navigation
    var state = this.props.commitsState;

    // have we loaded the initial data that populates this class yet?
    var data_keys = _.keys(Commits.getDataToLoad());
    if (!api.mapIsLoaded(this.props.data, data_keys)) {
      return <APINotLoaded 
        stateMap={this.props.data} 
        stateMapKeys={data_keys} 
        isInline={true}
      />;
    }

    // we may have fetched updated data...figure out which data to use
    var has_new_data = api.isLoaded(state.newData);
    var is_loading_new_data = state.newData !== undefined &&
      !api.isLoaded(state.newData);
    // copying a comment below: note that we might be called after we've
    // updated oldData but before we've updated newData

    if (has_new_data) {
      var commits = state.newData;
    } else {
      var commits = (state.oldData && state.oldData) || this.props.data.commits;
    }

    var project_info = this.props.project.getReturnedData();

    var style = is_loading_new_data ? {opacity: 0.5} : null;
    return <div style={style}>
      {this.renderTableControls()}
      {this.renderTable(commits.getReturnedData(), project_info)}
      {this.renderPaginationLinks(commits)}
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

    var cellClasses = ['nowrap buildWidgetCell', 'nowrap', 'nowrap', 'wide', 'nowrap', 'nowrap'];
    var headers = ['Last Build', 'Author', 'Commit', 'Name', 'Prev. B.', 'Committed'];

    return <Grid
      data={grid_data}
      cellClasses={cellClasses}
      headers={headers}
    />;
  },

  turnIntoRow: function(c, project_info) {
    var sha_abbr = c.sha.substr(0,5) + '...';
    var title = utils.first_line(c.message);

    var last_build = null, prev_builds = null;
    if (c.builds && c.builds.length > 0) {
      last_build = <BuildWidget build={_.first(c.builds)} />;
      if (c.builds.length > 1) {
        prev_builds = <span style={{opacity: "0.5"}}>
          {status_dots(c.builds.slice(1))}
        </span>;
      }
    }

    var author = 'unknown', author_page = null;
    var author_email = c.author && c.author.email;
    if (author_email) {
      author = utils.email_head(author_email);
      author_page = `/v2/author/${c.author.email}`;
    }

    var commit_page = null;
    if (c.builds && c.builds.length > 0) {
      var commit_page = '/v2/project_commit/' +
        project_info.slug + '/' +
        c.builds[0].source.id;
    }

    // TODO: if there are any comments, show a comment icon on the right
    return [
      last_build,
      author_page ? <a href={author_page}>{author}</a> : author,
      commit_page ? <a href={commit_page}>{sha_abbr}</a> : sha_abbr,
      title,
      prev_builds,
      <TimeText time={c.dateCreated} />
    ];
  },

  renderPaginationLinks: function(commits) {
    var hrefs = commits.getLinksFromHeader();

    var on_click = href => {
      // note that render() may be called after we've updated oldData but
      // before we've updated newData
      this.props.page.setState(utils.update_state_key(
        'commitsState', 'oldData', commits));
      // TODO: need to centralize this with api calls from table controls
      api.fetchMap(this.props.page, 'commitsState', {newData: href});
    };

    var links = [];
    if (hrefs.previous) {
      links.push(
        <a 
          className="marginRightS"
          href="#" 
          onClick={_.bind(on_click, this, hrefs.previous)}>
          Previous
        </a>
      );
    }

    if (hrefs.next) {
      links.push(
        <a 
          className="marginRightS" 
          href="#" 
          onClick={_.bind(on_click, this, hrefs.next)}>
          Next 
        </a>
      );
    }
    return <div className="marginBottomL marginTopS">{links}</div>;
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
    var data_keys = _.keys(ProjectDetails.getDataToLoad());
    if (!api.mapIsLoaded(this.props.data, data_keys)) {
      return <APINotLoaded 
        stateMap={this.props.data} 
        stateMapKeys={data_keys} 
      />;
    }

    var plans = this.props.data.details.getReturnedData();
    var project = this.props.project.getReturnedData();

    var markup = _.map(plans, p =>
      <div className="marginBottomL">
        <div style={{fontWeight: 900}}>{p.name}</div>
        <table className="invisibleTable">
        <tr>
          <td><b>Infrastructure:</b></td>
          <td>{!_.isEmpty(p.steps) && p.steps[0].name}</td>
        </tr> <tr>
          <td><b>Config:</b></td>
          <td> </td>
        </tr>
        </table>
        <pre className="commitMsg">
          {!_.isEmpty(p.steps) && p.steps[0].data}
        </pre>
      </div>
    );

    return <div>
      {this.renderHeader(project, plans)}
      {markup}
    </div>;

    /*
      <!-- If just one, inline. Otherwise, one per line -->
      <!-- stats -->
      <!-- or add a stats section... --> !!!
      */
  },

  renderHeader: function(project, plans) {
    var builds_on_diffs = project.options["phabricator.diff-trigger"];
    var builds_on_commits = project.options["build.commit-trigger"];

    var triggers = 'Does not automatically run';
    if (builds_on_commits && builds_on_diffs) {
      triggers = 'Diffs and Commits';
    } else if (builds_on_diffs) {
      triggers = 'Only diffs';
    } else if (builds_on_commits) {
      triggers = 'Only commits';
    }

    var branches_option = project.options["build.branch-names"];
    var branches = branches_option === "*" ? 
      'any' :
      branches_option.replace(/ /g, ", ");

    var whitelist_option = project.options["build.file-whitelist"].trim();
    var whitelist_paths = 'No path filter';
    if (whitelist_option) {
      whitelist_paths = _.map(utils.split_lines(whitelist_option), line => {
        <div>{line}</div>
      });
    }

    return <div className="marginBottomL">
      <span style={{fontWeight: 900}}>{project.name}</span>
      <table className="invisibleTable">
      <tr>
        <td><b>Repository:</b></td><td>{project.repository.url}</td>
      </tr> <tr>
        <td><b>Builds for:</b></td><td>{triggers}</td>
      </tr> <tr>
        <td><b>On branches:</b></td><td>{branches}</td>
      </tr> <tr>
        <td><b>Touching paths:</b></td><td>{whitelist_paths}</td>
      </tr> <tr>
        <td><b>Build plans</b></td><td>{plans.length}</td>
      </tr>
      </table>
    </div>;
    
    // TODO: how many tests? how many commits in the last week?
  }
});

/*
var Tests = React.createClass({

  statics: {
    getDataToLoad: function(project_slug) {
      return {};
    }
  },

  componentDidMount: function() {
    fetch_data(this, {
      testStats: '/api'
    });
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
  }
});
*/

export default ProjectPage;
