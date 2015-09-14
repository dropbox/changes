import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesLinks from 'es6!display/changes/links';
import SimpleTooltip from 'es6!display/simple_tooltip';
import { AjaxError } from 'es6!display/errors';
import { Grid } from 'es6!display/grid';
import { SingleBuildStatus, get_runnable_condition } from 'es6!display/changes/builds';
import { TimeText, display_duration } from 'es6!display/time';

import InteractiveData from 'es6!pages/helpers/interactive_data';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

var CommitsTab = React.createClass({

  propTypes: {
    // the project api response. Always loaded
    project: PropTypes.object,

    // InteractiveData...makes the chart interactive and paginates
    interactive: PropTypes.object,

    // parent elem that has state
    pageElem: PropTypes.element.isRequired,
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
      return <APINotLoaded calls={interactive.getDataToShow()} />;
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

      <input
        disabled={true}
        placeholder="Search by name or SHA [TODO]"
        style={{minWidth: 170, marginRight: 5}}
      />
    */
    return <div style={{marginBottom: 5, marginTop: 10}}>
      {branch_dropdown}
    </div>;
  },

  renderTable: function() {
    var data_to_show = this.props.interactive.getDataToShow().getReturnedData(),
      project_info = this.props.project.getReturnedData();

    var grid_data = _.map(data_to_show, c => this.turnIntoRow(c, project_info));

    var cellClasses = ['nowrap buildWidgetCell', 'nowrap', 'nowrap', 'nowrap', 'nowrap', 'wide', 'nowrap'];
    var headers = [
      'Last B.',
      'Time',
      'Tests Ran',
      'Commit',
      'Author',
      'Name',
      'Committed'
    ];

    return <Grid
      colnum={7}
      data={grid_data}
      cellClasses={cellClasses}
      headers={headers}
    />;
  },

  turnIntoRow: function(c, project_info) {
    var title = utils.truncate(utils.first_line(c.message));
    if (c.message.indexOf("!!skipthequeue") !== -1 ||
        c.message.indexOf("#skipthequeue") !== -1) { // we used to use this

      // dropbox-specific logic: we have a commit queue (oh hey, you should
      // build one of those too)

      title = <span>
        {title}
        <SimpleTooltip label="This commit bypassed the commit queue">
          <i className="fa fa-fast-forward blue marginLeftS" />
        </SimpleTooltip>
      </span>;
    }

    var build_widget = null, prev_builds = null, duration = null, tests = null;
    if (c.builds && c.builds.length > 0) {
      var sorted_builds = _.sortBy(c.builds, b => b.dateCreated).reverse();
      var last_build = _.first(sorted_builds);

      build_widget = <SingleBuildStatus
        build={last_build}
        parentElem={this}
      />;

      duration = get_runnable_condition(last_build) !== 'waiting' ?
        display_duration(last_build.duration / 1000) :
        null;

      tests = get_runnable_condition(last_build) !== 'waiting' ?
        last_build.stats.test_count :
        <span className="bluishGray">{last_build.stats.test_count}</span>;
    }

    // TODO: if there are any comments, show a comment icon on the right
    return [
      build_widget,
      <span className="bluishGray">{duration}</span>,
      <span className="bluishGray">{tests}</span>,
      ChangesLinks.phabCommit(c),
      ChangesLinks.author(c.author),
      title,
      <TimeText time={c.dateCommitted} />
    ];
  },

  renderPagination: function() {
    var links = this.props.interactive.getPaginationLinks();
    return <div className="marginBottomM marginTopM">{links}</div>;
  },
});

export default CommitsTab;
