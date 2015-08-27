import React from 'react';
import { OverlayTrigger, Tooltip } from 'react_bootstrap';

import APINotLoaded from 'es6!display/not_loaded';
import DisplayUtils from 'es6!display/changes/utils';
import { AjaxError } from 'es6!display/errors';
import { BuildWidget, status_dots } from 'es6!display/changes/builds';
import { Grid } from 'es6!display/grid';
import { TimeText } from 'es6!display/time';

import InteractiveData from 'es6!pages/helpers/interactive_data';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

var CommitsTab = React.createClass({

  propTypes: {
    // the project api response. Always loaded
    project: React.PropTypes.object,

    // InteractiveData...makes the chart interactive and paginates
    interactive: React.PropTypes.object,

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
    }
  },

  componentDidMount: function() {
    if (!this.props.interactive.hasRunInitialize()) {
      var params = this.props.isInitialTab ? InteractiveData.getParamsFromWindowUrl() : null;
      params = params || {};
      if (!params['branch']) {
        params['branch'] = this.props.project.getReturnedData()
          .repository.defaultBranch;
      }

      this.props.interactive.initialize(params || {});
    }

    // if we're revisiting this tab, let's restore the window url to the
    // current state
    if (api.isLoaded(this.props.interactive.getDataToShow())) {
      this.props.interactive.updateWindowUrl();
    }

    // TODO: maybe store this in parent state
    var repo_id = this.props.project.getReturnedData().repository.id;
    api.fetch(
      this,
      { 'branches': `/api/0/repositories/${repo_id}/branches` }
    );
  },

  render: function() {
    var interactive = this.props.interactive;

    if (interactive.hasNotLoadedInitialData()) {
      return <APINotLoaded
        state={interactive.getDataToShow()}
        isInline={true}
      />;
    }

    // we might be in the middle of / failed to load updated data
    var error_message = null;
    if (interactive.failedToLoadUpdatedData()) {
      error_message = <AjaxError response={interactive.getDataForErrorMessage().response} />;
    }

    var style = interactive.isLoadingUpdatedData() ? {opacity: 0.5} : null;

    return <div style={style}>
      {this.renderTableControls()}
      {error_message}
      {this.renderTable()}
      {this.renderPagination()}
    </div>;
  },

  renderTableControls: function() {
    // TODO: don't do default branch logic here, since we might be showing all
    // branches. If there's no branch, add a blank option to select

    var default_branch = this.props.project.getReturnedData()
      .repository.defaultBranch;
    var current_params = this.props.interactive.getCurrentParams();
    var current_branch = current_params.branch || default_branch;

    var branch_dropdown = null;
    if (api.isError(this.state.branches) &&
        this.state.branches.getStatusCode() === '422') {

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
        this.props.interactive.updateWithParams(
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
    var data_to_show = this.props.interactive.getDataToShow().getReturnedData(),
      project_info = this.props.project.getReturnedData();

    var grid_data = _.map(data_to_show, c => this.turnIntoRow(c, project_info));

    var cellClasses = ['nowrap buildWidgetCell', 'nowrap', 'nowrap', 'wide', 'nowrap', 'nowrap'];
    var headers = [
      'Last Build',
      'Author',
      'Commit',
      'Name',
      'Prev. B.',
      'Committed'
    ];

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
      sha_item = <a className="external" href={c.external.link} target="_blank">
        {sha_item}
      </a>;
    }

    var title = utils.first_line(c.message);
    if (c.message.indexOf("!!skipthequeue") !== -1 ||
        c.message.indexOf("#skipthequeue") !== -1) { // we used to use this

      // dropbox-specific logic: we have a commit queue (oh hey, you should
      // build one of those too)

      var tooltip = <Tooltip>
        This commit bypassed the commit queue
      </Tooltip>;

      title = <span>
        {title}
        <OverlayTrigger placement="bottom" overlay={tooltip}>
          <i className="fa fa-fast-forward lt-magenta marginLeftS" />
        </OverlayTrigger>
      </span>;
    }

    var build_widget = null, prev_builds = null;
    if (c.builds && c.builds.length > 0) {
      var sorted_builds = _.sortBy(c.builds, b => b.dateCreated).reverse();
      var last_build = _.first(sorted_builds);
      build_widget = <BuildWidget build={last_build} parentElem={this} />;
      if (sorted_builds.length > 1) {
        prev_builds = <span style={{opacity: "0.5"}}>
          {status_dots(sorted_builds.slice(1))}
        </span>;
      }
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

  renderPagination: function() {
    var links = this.props.interactive.getPaginationLinks();
    return <div className="marginBottomM marginTopM">{links}</div>;
  },
});

export default CommitsTab;
