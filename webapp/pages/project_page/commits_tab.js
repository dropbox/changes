import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesLinks from 'es6!display/changes/links';
import SimpleTooltip from 'es6!display/simple_tooltip';
import { AjaxError } from 'es6!display/errors';
import { ChangesChart } from 'es6!display/changes/charts';
import { Grid } from 'es6!display/grid';
import { SingleBuildStatus } from 'es6!display/changes/builds';
import { TimeText, display_duration } from 'es6!display/time';
import { get_runnable_condition } from 'es6!display/changes/build_conditions';

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
    pageElem: PropTypes.object.isRequired,
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
      <div className="floatR">
        {this.renderChart()}
      </div>
      {this.renderTableControls()}
      {error_message}
      {this.renderTable()}
      {this.renderPaging()}
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

      branch_dropdown = <div className="selectWrap">
        <select disabled={true}>
          <option>No branches</option>
        </select>
      </div>;
    } else if (!api.isLoaded(this.state.branches)) {
      branch_dropdown = <div className="selectWrap">
        <select disabled={true}>
          <option value={current_branch}>{current_branch}</option>
        </select>
      </div>;
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

      branch_dropdown = <div className="selectWrap">
        <select onChange={onChange} value={current_branch}>
          {options}
        </select>
      </div>;
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
    return <div 
      className="commitsControls" 
      style={{marginBottom: 5, marginTop: 10}}>
      {branch_dropdown}
    </div>;
  },

  renderChart() {
    var interactive = this.props.interactive;
    var dataToShow = interactive.getDataToShow().getReturnedData();

    var builds = _.map(dataToShow, commit => {
      if (commit.builds && commit.builds.length > 0) {
        var sortedBuilds = _.sortBy(commit.builds, b => b.dateCreated).reverse();
        return _.first(sortedBuilds);
      } else {
        return {};
      }
    });

    var links = interactive.getPagingLinks({type: 'chart_paging'});
    var prevLink = interactive.hasPreviousPage() ? links[0] : '';
    var nextLink = interactive.hasNextPage() ? links[1] : '';

    return <div className="commitsChart">
      {prevLink}
      <ChangesChart
        type="build"
        className="inlineBlock"
        runnables={builds}
        enableLatest={!interactive.hasPreviousPage()}
      />
      {nextLink}
    </div>;
  },

  renderTable: function() {
    var data_to_show = this.props.interactive.getDataToShow().getReturnedData(),
      project_info = this.props.project.getReturnedData();

    var grid_data = _.map(data_to_show, c => this.turnIntoRow(c, project_info));

    var cellClasses = [
      'buildWidgetCell', 
      'wide easyClick', 
      'bluishGray nowrap', 
      'bluishGray nowrap', 
      'nowrap', 
      'nowrap', 
      'nowrap'
    ];

    var headers = [
      'Result',
      'Name',
      'Time',
      'Tests Ran',
      'Author',
      'Commit',
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

      tests = last_build.stats.test_count;

      title = <a className="subtle" href={ChangesLinks.buildHref(last_build)}>
        {title}
      </a>;
    }

    // TODO: if there are any comments, show a comment icon on the right
    return [
      build_widget,
      title,
      duration,
      tests,
      ChangesLinks.author(c.author),
      ChangesLinks.phabCommit(c),
      <TimeText key={c.id} time={c.dateCommitted} />
    ];
  },

  renderPaging: function() {
    var links = this.props.interactive.getPagingLinks();
    return <div className="marginBottomM marginTopM">{links}</div>;
  },
});

export default CommitsTab;
