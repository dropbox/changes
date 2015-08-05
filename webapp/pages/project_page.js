import React from 'react';
import { Popover, OverlayTrigger } from 'react_bootstrap';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesPage from 'es6!display/page_chrome';
import DisplayUtils from 'es6!display/changes/utils';
import { AjaxError, ProgrammingError } from 'es6!display/errors';
import { BuildWidget, status_dots, get_build_cause } from 'es6!display/changes/builds';
import { Grid } from 'es6!display/grid';
import { Menu1, Menu2, MenuUtils } from 'es6!display/menus';
import { TimeText } from 'es6!display/time';

import DataControls from 'es6!pages/helpers/data_controls';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';
import colors from 'es6!utils/colors';

var cx = React.addons.classSet;

var ProjectPage = React.createClass({

  getInitialState: function() {
    return {
      selectedItem: null, // we set this in componentWillMount
      project: null,
      commits: null,
      details: null,

      // Keep the state for the commit tab here (and send it via props.) This
      // preserves the state if the user clicks to another tab
      commitsState: {},

      // same, but for builds state
      buildsControls: {}
    }
  },

  menuItems: [
    'Commits', 
    'Builds',
    'Tests [TODO]', 
    'Project Details'
  ],

  componentWillMount: function() {
    // if our url contains a hash, show that tab
    var selected_item_from_hash = MenuUtils.selectItemFromHash(
      window.location.hash, this.menuItems);

    this.setState({ selectedItem: selected_item_from_hash || 'Commits' });

    // initialize our pagination objects. Data fetching still doesn't happen
    // till componentDidMount (either ours or the subcomponent.)
    this.setState({
      buildsControls: DataControls(
        this, 
        'buildsControls', 
        Builds.getEndpoint(this.props.projectSlug)),

      commitsControls: DataControls(
        this, 
        'commitsControls', 
        Commits.getEndpoint(this.props.projectSlug))
    });
  },

  componentDidMount: function() {
    var slug = this.props.projectSlug;

    // grab the initial project data needed to render anything. We also eagerly 
    // grab some data for our tabs so that they load faster
    api.fetch(this, {
      project: `/api/0/projects/${slug}`,
      details: ProjectDetails.getAPIEndpoint(slug)
    });

    Commits.doDataFetching(this.state.commitsControls);
  },

  render: function() {
    if (!api.isLoaded(this.state.project)) {
      return <APINotLoaded state={this.state.project} />;
    }

    // render menu
    var selected_item = this.state.selectedItem;
    var onClick = item => {
      if (item === selected_item) {
        return;
      }

      window.history.replaceState(
        null,
        'changed tab',
        URI(window.location.href)
          .search("")
          .hash(item.replace(/ /g, ""))
          .toString()
      );
      this.setState({selectedItem: item});
    }
    var menu = <Menu2 
      items={this.menuItems} 
      selectedItem={selected_item} 
      onClick={onClick}
    />;

    var content = null;
    switch (selected_item) {
      case 'Commits':
        content = <Commits
          project={this.state.project}
          controls={this.state.commitsControls}
          pageElem={this}
        />;
        break;
      case 'Builds':
        content = <Builds
          project={this.state.project}
          controls={this.state.buildsControls}
          pageElem={this}
        />;
        break;
      case 'Tests [TODO]':
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

    var branches_option = project_info.options["build.branch-names"] || '*';
    if (branches_option === "*") {
      var branches = "all branches";
    } else if (branches_option.split(" ").length === 1) {
      var branches = `only on ${branches_option} branch`;
    } else {
      var branches = "branches: " + branches_option.replace(/ /g, ", ");
    }

    // TODO: add tooltip to "certain paths"
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
    // the project api response. Always loaded
    project: React.PropTypes.object,

    // controls
    controls: React.PropTypes.object,

    // parent elem that has state
    pageElem: React.PropTypes.element.isRequired,
  },

  getInitialState: function() {
    // powers on-hover list of failed tests. Its ok for this to get wiped out
    // every time we switch tabs
    return { failedTests: [] };
  },

  statics: {
    getEndpoint: function(project_slug) {
      return URI(`/api/0/projects/${project_slug}/commits/`)
        .query({ 'all_builds': 1 })
        .toString();
    },

    doDataFetching: function(controls, is_selected_tab) {
      // if the user is loading this tab on a new full page load, use the page url
      // query params as the api parameters (allows link sharing)
      var params = is_selected_tab ? DataControls.getParamsFromWindowUrl() : null;
      params = params || {};

      controls.initialize(params);
    },
  },

  componentDidMount: function() {
    // if we're revisiting this tab, let's restore the window url to the
    // current state
    if (api.isLoaded(this.props.controls.getDataToShow())) {
      this.props.controls.updateWindowUrl();
    }

    // TODO: maybe store this in parent state
    var repo_id = this.props.project.getReturnedData().repository.id;
    api.fetch(
      this,
      { 'branches': `/api/0/repositories/${repo_id}/branches` }
    );
  },

  render: function() {
    var controls = this.props.controls;

    if (controls.hasNotLoadedInitialData()) {
      return <APINotLoaded 
        state={controls.getDataToShow()} 
        isInline={true} 
      />;
    }

    // we might be in the middle of / failed to load updated data
    var error_message = null;
    if (controls.failedToLoadUpdatedData()) {
      error_message = <AjaxError response={controls.getDataForErrorMessage().response} />;
    }

    var style = controls.isLoadingUpdatedData() ? {opacity: 0.5} : null;

    return <div style={style}>
      {this.renderTableControls()}
      {error_message}
      {this.renderTable()}
      {this.renderPagination()}
    </div>;
  },

  renderTableControls: function() {
    var default_branch = this.props.project.getReturnedData()
      .repository.defaultBranch;
    var current_params = this.props.controls.getCurrentParams();
    var current_branch = current_params.branch || default_branch;

    var branch_dropdown = null;
    if (api.isError(this.state.branches) && 
        this.state.branches.getStatusCode() + "" === '422') {

      branch_dropdown = <select disabled={true}>
        <option>No branches</option>
      </select>;
    } else if (!api.isLoaded(this.state.branches)) {
      branch_dropdown = <select disabled={true}>
        <option value={current_branch}>{current_branch}</option>
      </select>;
    } else {
      var options = _.chain(this.state.branches.getReturnedData())
        .pluck('name')
        .sortBy(_.identity)
        .map(n => <option value={n}>{n}</option>)
        .value();

      var onChange = evt => {
        this.props.controls.updateWithParams(
          { branch: evt.target.value },
          true); // reset to page 0
      };

      branch_dropdown = <select onChange={onChange} value={current_branch}>
        {options}
      </select>;
    }
    
    /*
    <span className="paddingLeftS">
      Showing most recent diffs since 0:00pm
    </span>
    */
    return <div style={{marginBottom: 5, marginTop: 10}}>
      <input 
        disabled={true}
        placeholder="Search by name or SHA [TODO]"
        style={{minWidth: 170, marginRight: 5}}
      />
      {branch_dropdown}
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

  renderTable: function() {
    var data_to_show = this.props.controls.getDataToShow().getReturnedData(),
      project_info = this.props.project.getReturnedData();

    var grid_data = _.map(data_to_show, c => this.turnIntoRow(c, project_info));

    var cellClasses = ['nowrap buildWidgetCell', 'nowrap', 'nowrap', 'wide', 'nowrap', 'nowrap'];
    var headers = ['Last Build', 'Author', 'Commit', 'Name', 'Prev. B.', 'Committed'];

    return <Grid
      colnum={6}
      data={grid_data}
      cellClasses={cellClasses}
      headers={headers}
    />;
  },

  turnIntoRow: function(c, project_info) {
    var sha_item = c.sha.substr(0,7);
    if (c.external && c.external.link) {
      sha_item = <a classname="external" href={c.external.link} target="_blank">
        {sha_item}
      </a>;
    }

    var title = utils.first_line(c.message);

    var build_widget = null, prev_builds = null;
    if (c.builds && c.builds.length > 0) {
      var last_build = _.first(c.builds);
      build_widget = <BuildWidget build={last_build} />;
      if (c.builds.length > 1) {
        prev_builds = <span style={{opacity: "0.5"}}>
          {status_dots(c.builds.slice(1))}
        </span>;
      }

      if (last_build.stats['test_failures'] > 0) {
        build_widget = this.showFailuresOnHover(last_build, build_widget);
      }
    }

    var commit_page = null;
    if (c.builds && c.builds.length > 0) {
      var commit_page = '/v2/project_commit/' +
        project_info.slug + '/' +
        c.builds[0].source.id;
    }

    // TODO: if there are any comments, show a comment icon on the right
    return [
      build_widget,
      DisplayUtils.authorLink(c.author),
      sha_item,
      title,
      prev_builds,
      <TimeText time={c.dateCommitted} />
    ];
  },

  showFailuresOnHover: function(build, build_widget) {
    var popover = null;
    if (api.isLoaded(this.state.failedTests[build.id])) {
      var data = this.state.failedTests[build.id].getReturnedData();
      var list = _.map(data.testFailures.tests, t => {
        return <div>{_.last(t.name.split("."))}</div>;
      });
      if (data.testFailures.tests.length < build.stats['test_failures']) {
        list.push(
          <div className="marginTopS"> <em>
            Showing{" "}
            {data.testFailures.tests.length} 
            {" "}out of{" "}
            {build.stats['test_failures']} 
            {" "}test failures
          </em> </div>
        );
      }

      var popover = <Popover className="popoverNoMaxWidth">
        <span className="bb">Failed Tests:</span>
        {list}
      </Popover>;
    } else {
      // we want to fetch more build information and show a list of failed
      // tests on hover. To do this, we'll create an anonymous react element
      // that does data fetching on mount
      var data_fetcher_defn = React.createClass({
        componentDidMount() {
          var elem = this.props.elem,
            build_id = this.props.buildID;
          if (!elem.state.failedTests[build_id]) {
            api.fetchMap(elem, 'failedTests', {
              [ build_id ]: `/api/0/builds/${build_id}/`
            });
          }
        },

        render() {
          return <span />;
        }
      });

      var data_fetcher = React.createElement(
        data_fetcher_defn, 
        {elem: this, buildID: build.id}
      );

      var popover = <Popover>
        {data_fetcher}
        Loading failed test list
      </Popover>;
    }

    return <div>
      <OverlayTrigger 
        trigger='hover' 
        placement='right' 
        overlay={popover}>
        <div>{build_widget}</div>
      </OverlayTrigger>
    </div>;
  },

  renderPagination: function() {
    var links = this.props.controls.getPaginationLinks();
    return <div>{links}</div>;
  },
});

var Builds = React.createClass({

  propTypes: {
    // the project api response
    project: React.PropTypes.object,

    // state is handled by parent so that its preserved if someone selects 
    // another tab
    myState: React.PropTypes.object,

    // The datacontrols object that handles dealing with data
    controls: React.PropTypes.object,

    // parent elem that has state
    pageElem: React.PropTypes.element.isRequired,
  },

  statics: {
    getEndpoint: function(slug) {
      return `/api/0/projects/${slug}/builds/`;
    }
  },

  componentDidMount: function() {
    this.props.controls.initialize(DataControls.getParamsFromWindowUrl());

    // if this table has data to render, let's make sure the window url is
    // correct
    if (api.isLoaded(this.props.controls.getDataToShow())) {
      this.props.controls.updateWindowUrl();
    }
  },

  render: function() {
    var controls = this.props.controls;

    if (controls.hasNotLoadedInitialData()) {
      return <APINotLoaded 
        state={controls.getDataToShow()} 
        isInline={true} 
      />;
    }

    var data_to_show = controls.getDataToShow();

    var data = _.map(data_to_show.getReturnedData(), build => {
      var target = null;
      if (_.contains(build.tags, 'arc test')) {
        target = '';
      } else if (build.source.patch) {
        target = <a 
          className="external" 
          href={build.source.data['phabricator.revisionURL']}
          target="_blank">
          {'D' + build.source.data['phabricator.revisionID']}
        </a>
      } else {
        target = build.source.revision.sha.substr(0, 7);
      }

      return [
        <BuildWidget build={build} />,
        target,
        DisplayUtils.authorLink(build.author),
        build.name,
        get_build_cause(build),
        <TimeText time={build.dateStarted} />
      ];
    });

    var cellClasses = ['buildWidgetCell', 'nowrap', 'nowrap', 'wide', 'nowrap', 'nowrap'];

    var headers = [
      'Result',
      'Target',
      'By',
      'Name',
      'Cause',
      'Started'
    ];

    var error_message = null;
    if (controls.failedToLoadUpdatedData()) {
      error_message = <AjaxError response={controls.getDataForErrorMessage().response} />;
    }

    var style = controls.isLoadingUpdatedData() ? {opacity: 0.5} : null;

    return <div>
      {this.renderControls()}
      {error_message}
      <div style={style}>
        <Grid
          colnum={6}
          cellClasses={cellClasses}
          data={data}
          headers={headers}
        />
      </div>
      {this.renderPagination()}
    </div>;
  },

  renderControls: function(commits) {
    var items = [
      'All',
      'Commits Only',
      'Diffs/arc test only'
    ];

    var params_for_items = {
      'All': {
        'include_patches': 1,
        'patches_only': 0 
      },
      'Commits Only': {
        'include_patches': 0,
        'patches_only': 0 
      },
      'Diffs/arc test only': {
        'include_patches': 1,
        'patches_only': 1 
      }
    };

    var current_params = this.props.controls.getCurrentParams();
    var selected_item = 'All';
    _.each(params_for_items, (params, item) => {
      var is_selected = true;
      _.each(params, (v,k) => {
        if (current_params[k]+"" !== v+"") {
          is_selected = false;
        }
      });
      if (is_selected) {
        selected_item = item;
      }
    });

    var onclick = item => this.props.controls.updateWithParams(params_for_items[item], true);

    return <Menu1
      items={items}
      selectedItem={selected_item} 
      onClick={onclick}
    />;
  },

  renderPagination: function(commits) {
    var links = this.props.controls.getPaginationLinks();
    return <div>{links}</div>;
  },
});

var TODO = React.createClass({
  render: function() {
    return <div>TODO</div>;
  }
});

var ProjectDetails = React.createClass({

  propTypes: {
    // the API response from getAPIEndpoint below
    data: React.PropTypes.object,
    // the project api response
    project: React.PropTypes.object,
  },

  statics: {
    getAPIEndpoint: function(project_slug) {
      return `/api/0/projects/${project_slug}/plans/`;
    }
  },

  render: function() {
    if (!api.isLoaded(this.props.data)) {
      return <APINotLoaded state={this.props.data} />;
    }

    var plans = this.props.data.getReturnedData();
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

    var branches_option = project.options["build.branch-names"] || '*';
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
