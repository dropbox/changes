import React from 'react';
import { Popover, OverlayTrigger } from 'react_bootstrap';

import APINotLoaded from 'es6!display/not_loaded';
import DisplayUtils from 'es6!display/changes/utils';
import { BuildWidget, status_dots } from 'es6!display/changes/builds';
import { Grid } from 'es6!display/grid';
import { TimeText } from 'es6!display/time';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

var CommitsTab = React.createClass({

  propTypes: {
    // the data fetch specified in getAPIEndpoint
    data: React.PropTypes.object,

    // the project api response. Always loaded
    project: React.PropTypes.object,

    // branches api response
    branches: React.PropTypes.object,

    // state is handled by parent so that its preserved if someone selects
    // the tests or details tab
    myState: React.PropTypes.object,

    // parent elem that has state
    pageElem: React.PropTypes.element.isRequired,
  },

  getInitialState: function() {
    // powers on-hover list of failed tests. Easier to just do this rather
    // than using myState above (it doesn't really matter if this gets wiped
    // out)
    return { failedTests: [] };
  },

  statics: {
    getAPIEndpoint: function(project_slug) {
      var params = URI(window.location.href).query(true);
      return URI(`/api/0/projects/${project_slug}/commits/`)
        .query(_.extend(params, { 'all_builds': 1 }))
        .toString();
    },
  },

  render: function() {
    var state = this.props.myState;

    if (!api.isLoaded(this.props.data)) {
      return <APINotLoaded
        state={this.props.data}
        isInline={true}
      />;
    }

    // we also need a list of repo branches, which we can't fetch on page load
    // because we don't know the repo id.. Send that ajax call immediately
    // after we load.

    // TODO: just make the api more flexible...
    if (!state['sending_branches_ajax_call']) {
      var repo_id = this.props.project.getReturnedData().repository.id;

      utils.async(__ => {
        this.props.pageElem.setState(
          utils.update_key_in_state_dict(
            'commitsState',
            'sending_branches_ajax_call',
            true),
          ___ => {
            api.fetchMap(
              this.props.pageElem,
              'commitsState',
              { 'branches': `/api/0/repositories/${repo_id}/branches` }
            );
          }
        );
      }.bind(this));
    }

    var is_loading_new_data = this.isLoadingNewData();
    var commits = this.getCurrentData();
    var project_data = this.props.project.getReturnedData();

    var style = is_loading_new_data ? {opacity: 0.5} : null;
    return <div style={style}>
      {this.renderTableControls()}
      {this.renderTable(commits.getReturnedData(), project_data)}
      {this.renderPaginationLinks(commits)}
    </div>;
  },

  renderTableControls: function() {
    var state = this.props.myState,
      project = this.props.project.getReturnedData();

    var branches = null;
    if (project.repository.defaultBranch) {
      var branches = <select disabled={true}>
        <option value={project.defaultBranch}>{project.defaultBranch}</option>
      </select>;
    } else {
      var branches = <select disabled={true}>
        <option>Unknown branch</option>
      </select>;
    }

    if (api.isLoaded(state.branches)) {
      var selected = this.getNewestQueryParams()['branch'] ||
        project.repository.defaultBranch;

      var options = _.chain(state.branches.getReturnedData())
        .pluck('name')
        .sortBy(_.identity)
        .map(n => <option value={n}>{n}</option>)
        .value();

      var onChange = evt => {
        this.updateData({ branch: evt.target.value });
      };

      branches = <select onChange={onChange} value={selected}>{options}</select>;
    } else if (api.isError(state.branches) &&
               state.branches.getStatusCode() + "" === '422') {
      branches = <select disabled={true}>
        <option>no branches</option>
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
      {branches}
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
    // we want to fetch more build information and show a list of failed
    // tests on hover
    var data_fetcher_defn = React.createClass({
      // ok to use shortcut object syntax for this inner element
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

  renderPaginationLinks: function(commits) {
    var hrefs = commits.getLinksFromHeader();

    // the pagination api should return the same endpoint that we're already
    // using, so we'll just grab the get params
    var on_click = href => this.updateData(URI(href).query(true));

    var links = [];
    if (hrefs.previous) {
      links.push(
        <a
          className="marginRightS"
          href={'#' || hrefs.previous}
          onClick={on_click.bind(this, hrefs.previous)}>
          Previous
        </a>
      );
    }

    if (hrefs.next) {
      links.push(
        <a
          className="marginRightS"
          href={'#' || hrefs.next}
          onClick={on_click.bind(this, hrefs.next)}>
          Next
        </a>
      );
    }
    return <div className="marginBottomL marginTopS">{links}</div>;
  },

  updateData: function(new_params) {
    // TODO: straigten this out :(
    window.history.replaceState(
      null,
      'updating commits page',
      URI(window.location.href).query(_.omit(new_params, ['all_builds'])));

    // note that render() may be called after we've updated oldData but
    // before we've updated newData
    this.props.pageElem.setState(utils.update_key_in_state_dict(
      'commitsState', 'preloadData', this.getCurrentData()));

    var slug = this.props.project.getReturnedData().slug;
    var href = URI(`/api/0/projects/${slug}/commits/`)
      .query(_.extend(new_params, { 'all_builds': 1 }))
      .toString();
    api.fetchMap(this.props.pageElem, 'commitsState', {newestData: href});
  },

  hasEverUpdatedData: function() {
    var state = this.props.myState;

    return state.preloadData !== undefined;
  },

  isLoadingNewData: function() {
    var state = this.props.myState;

    return state.newestData !== undefined && !api.isLoaded(state.newestData);
  },

  getCurrentData: function() {
    var state = this.props.myState;

    if (state.newestData && api.isLoaded(state.newestData)) {
      return state.newestData;
    } else if (this.hasEverUpdatedData()) {
      return state.preloadData;
    }
    return this.props.data;
  },

  getNewestQueryParams: function() {
    var state = this.props.myState;

    var endpoint = (state.newestData && state.newestData.endpoint) ||
      (state.preloadData && state.preloadData.endpoint) ||
      this.props.data.endpoint;

    return URI(endpoint).query(true);
  },
});

export default CommitsTab;
