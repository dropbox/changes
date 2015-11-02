import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import SectionHeader from 'es6!display/section_header';
import { AjaxError } from 'es6!display/errors';
import ChangesLinks from 'es6!display/changes/links';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import { Grid, GridRow } from 'es6!display/grid';
import { Tabs, MenuUtils } from 'es6!display/menus';
import { TestDetails } from 'es6!display/changes/test_details';

import InteractiveData from 'es6!pages/helpers/interactive_data';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

var BuildTestsPage = React.createClass({

  menuItems: [
    'Sharding',
    'Not Passing Tests',
    'Slow Tests',
    'Retries'
  ],

  getInitialState: function() {
    return {
      selectedItem: null, // set in componentWillMount

      // Not Passing tab
      expandedTests: {},  // expand for more details
      uncheckedResults: {},  // checkboxes to filter by statuses

      // Retries tab
      expandedRetryTests: {},
    }
  },

  componentWillMount: function() {
    var selectedItemFromHash = MenuUtils.selectItemFromHash(
      window.location.hash, this.menuItems);

    // when we first came to this page, which tab was shown? Used by the
    // initial data fetching within tabs
    this.initialTab = selectedItemFromHash || 'Not Passing Tests';

    this.setState({ selectedItem: this.initialTab });

    this.setState({
      slowTests : InteractiveData(this,
        'slowTests',
        `/api/0/builds/${this.props.buildID}/tests/?sort=duration`),

      retries : InteractiveData(this,
        'retries',
        `/api/0/builds/${this.props.buildID}/tests/?sort=retries`),
    });
  },

  componentDidMount: function() {
    _.each([['slowTests', 'Slow Tests'], ['retries', 'Retries']], tabs => {
      var [stateKey, tabName] = tabs;
      var params = {};
      if (this.initialTab === tabName) {
        var params = InteractiveData.getParamsFromWindowUrl();
      }
      this.state[stateKey].initialize(params);
    });

    api.fetch(this, {
      buildInfo: `/api/0/builds/${this.props.buildID}`,
      failedTests: `/api/0/builds/${this.props.buildID}/tests/failures`
    });
  },

  render: function() {
    if (!api.isLoaded(this.state.buildInfo)) {
      return <APINotLoadedPage calls={this.state.buildInfo} />;
    }
    var buildInfo = this.state.buildInfo.getReturnedData();

    var buildTitle = `${buildInfo.project.name} Build`
    var pageTitle = 'Tests for ' + buildTitle;
    utils.setPageTitle(pageTitle);

    // render menu
    var selectedItem = this.state.selectedItem;

    var menu = <Tabs
      items={this.menuItems}
      selectedItem={selectedItem}
      onClick={MenuUtils.onClick(this, selectedItem)}
    />;

    var content = null;
    switch (selectedItem) {
      case 'Sharding':
        content = <ShardingTab build={buildInfo} />;
        break;
      case 'Not Passing Tests':
        content = this.renderFailed();
        break;
      case 'Slow Tests':
        content = this.renderSlow();
        break;
      case 'Retries':
        content = this.renderRetries();
        break;
      default:
        throw 'unreachable';
    }

    return <ChangesPage highlight="Projects">
      <SectionHeader>Tests for <a href={ChangesLinks.buildHref(buildInfo)}>{buildTitle}</a></SectionHeader>
      {menu}
      <div className="marginTopS">{content}</div>
    </ChangesPage>;
  },

  renderFailed: function() {
    if (!api.isLoaded(this.state.failedTests)) {
      return <APINotLoaded state={this.state.failedTests} />;
    }
    var failedTests = this.state.failedTests.getReturnedData();

    if (!failedTests) {
      return <div>Empty</div>;
    }

    var project_id = this.state.buildInfo.getReturnedData().project.id;

    var rows = [];
    _.each(failedTests, test => {
      // skip 'quarantined_passed' tests
      if (test.result.indexOf('passed') >= 0) {
        return;
      } else if (this.state.uncheckedResults[test.result]) {
        return;
      }

      var href = `/project_test/${project_id}/${test.hash}`;

      var onClick = __ => {
        this.setState(
          utils.update_key_in_state_dict('expandedTests',
            test.test_id,
            !this.state.expandedTests[test.test_id])
        );
      };

      var expandLabel = !this.state.expandedTests[test.test_id] ?
        'Expand' : 'Collapse';

      var markup = <div>
        {test.shortName} <a onClick={onClick}>{expandLabel}</a>
        <div className="subText">{test.name}</div>
      </div>;

      var capitalizedResult = test.result.charAt(0).toUpperCase() +
        test.result.slice(1);

      var color = 'bluishGray';
      if (test.result.indexOf('failed') >= 0) {
        color = 'red';
      }

      rows.push([
        markup,
        <span className={color}>{capitalizedResult}</span>,
        <a href={href}>History</a>,
      ]);

      if (this.state.expandedTests[test.test_id]) {
        rows.push(GridRow.oneItem(
          <TestDetails testID={test.test_id} />
        ));
      }
    });

    var tests_by_result = _.groupBy(failedTests, t => t.result);
    var result_markup = _.map(tests_by_result, (tests, result) => {
      // as above, skip 'quarantined_passed' tests
      if (result.indexOf('passed') >= 0) {
        return;
      }

      var sentence = utils.plural(tests.length, "test(s) " + result);
      // render the number ourselves
      var rest_of_words = _.rest(sentence.split(" ")).join(" ");

      var onClick = evt => {
        this.setState(
          utils.update_key_in_state_dict(
            'uncheckedResults',
            result,
            !this.state.uncheckedResults[result]
          )
        );
      };

      var isChecked = !this.state.uncheckedResults[result];

      return <div className="marginTopS">
        <label>
          <input type="checkbox" checked={isChecked} onClick={onClick} />
          <span className="marginLeftXS lb">{tests.length}</span>
          {" "}
          {rest_of_words}
        </label>
      </div>;
    });

    return <div>
      {result_markup}
      <Grid
        colnum={3}
        className="marginBottomM marginTopM"
        cellClasses={['wide', 'nowrap', 'nowrap']}
        data={rows}
        headers={['Name', 'Result', 'Links']}
      />
    </div>;
  },

  renderSlow: function() {
    var slowTestsInteractive = this.state.slowTests;

    // we want to update the window url whenever the user switches tabs
    slowTestsInteractive.updateWindowUrl();

    if (slowTestsInteractive.hasNotLoadedInitialData()) {
      return <APINotLoaded calls={slowTestsInteractive.getDataToShow()} />;
    }

    var slowTests = slowTestsInteractive.getDataToShow().getReturnedData();

    var rows = [];
    _.each(slowTests, test => {
      rows.push([
        test.name,
        test.duration
      ]);
    });

    var errorMessage = null;
    if (slowTestsInteractive.failedToLoadUpdatedData()) {
      errorMessage = <AjaxError response={slowTestsInteractive.getDataForErrorMessage().response} />;
    }
    var style = slowTestsInteractive.isLoadingUpdatedData() ? {opacity: 0.5} : null;

    var pagingLinks = slowTestsInteractive.getPagingLinks();

    return <div style={style}>
      {errorMessage}
      <Grid
        colnum={2}
        className="marginBottomM marginTopM"
        data={rows}
        headers={['Name', 'Duration (ms)']}
      />
      <div className="marginTopM marginBottomM">
        {pagingLinks}
      </div>
    </div>;
  },

  renderRetries: function() {
    var retriesInteractive = this.state.retries;

    // we want to update the window url whenever the user switches tabs
    retriesInteractive.updateWindowUrl();

    if (retriesInteractive.hasNotLoadedInitialData()) {
      return <APINotLoaded calls={retriesInteractive.getDataToShow()} />;
    }

    var retries = retriesInteractive.getDataToShow().getReturnedData();

    var rows = [];
    _.each(retries, test => {
      var onClick = __ => {
        this.setState(
          utils.update_key_in_state_dict('expandedRetryTests',
            test.id,
            !this.state.expandedRetryTests[test.id])
        );
      };

      var expandLabel = !this.state.expandedRetryTests[test.id] ?
        'Expand' : 'Collapse';

      var markup = <div>
        {test.shortName} <a onClick={onClick}>{expandLabel}</a>
        <div className="subText">{test.name}</div>
      </div>;

      rows.push([
        markup,
        test.numRetries
      ]);

      if (this.state.expandedRetryTests[test.id]) {
        rows.push(GridRow.oneItem(
          <TestDetails testID={test.id} />
        ));
      }
    });

    var errorMessage = null;
    if (retriesInteractive.failedToLoadUpdatedData()) {
      errorMessage = <AjaxError response={retriesInteractive.getDataForErrorMessage().response} />;
    }
    var style = retriesInteractive.isLoadingUpdatedData() ? {opacity: 0.5} : null;

    var pagingLinks = retriesInteractive.getPagingLinks();

    return <div style={style}>
      {errorMessage}
      <Grid
        colnum={2}
        className="marginBottomM marginTopM"
        data={rows}
        headers={['Name', 'Retries']}
      />
      <div className="marginTopM marginBottomM">
        {pagingLinks}
      </div>
    </div>;
  },
});

var ShardingTab = React.createClass({

  getInitialState: function() {
    var jobPhases = {};
    _.each(this.props.build.jobs, j => {
      jobPhases[j.id] = null;
    });

    return {
      jobPhases: jobPhases,
      // TODO: move to parent...
      expandedShards: {}
    };
  },

  componentDidMount: function() {
    // phases/jobsteps info
    var jobIDs = _.map(this.props.build.jobs, j => j.id);

    var endpoint_map = {};
    _.each(jobIDs, id => {
      endpoint_map[id] = `/api/0/jobs/${id}/phases?test_counts=1`;
    });

    // TODO: don't refetch every time (cache on parent)
    api.fetchMap(this, 'jobPhases', endpoint_map);
  },

  render: function() {
    var build = this.props.build;
    var jobIDs = _.map(build.jobs, j => j.id);

    var phasesCalls = _.chain(this.state.jobPhases)
      .pick(jobIDs)
      .values().value();

    if (!api.allLoaded(phasesCalls)) {
      return <APINotLoaded calls={phasesCalls} />;
    }

    var markup = [];
    _.each(jobIDs, jobID => {
      var job = _.filter(build.jobs, j => j.id === jobID)[0];
      markup.push(<SectionHeader>{job.name}</SectionHeader>);
      var rows = [];
      _.each(this.state.jobPhases[jobID].getReturnedData(), phase => {
        // Filter out steps with missing weights and then sort by descending weight.
        var steps = _.sortBy(_.filter(phase.steps, step => step.data.weight),
                             step => -step.data.weight);
        _.each(steps, step => {
          var onClick = evt => {
            this.setState(utils.update_key_in_state_dict(
              'expandedShards',
              step.node.name,
              !this.state.expandedShards[step.node.name]
            ));
          };

          var expandLabel = !this.state.expandedShards[step.node.name] ?
            'See Raw Data' : 'Collapse';
          
          rows.push([
            step.node && step.node.name,
            step.data.weight,
            step.data.tests.length,
            <a onClick={onClick}>{expandLabel}</a>
          ]);

          if (this.state.expandedShards[step.node.name]) {
            rows.push(GridRow.oneItem(
              <pre className="defaultPre">
                {JSON.stringify(step.data, null, 2)}
              </pre>
            ));
          }

          rows.push(GridRow.oneItem(
            <div>
              <b>Files:</b>
              <pre>{step.data.tests.join("\n")}</pre>
            </div>
          ));
        });
      });
      markup.push(
        <Grid
          colnum={4}
          headers={['Node', 'Shard Weight', 'File Count', 'Links']}
          cellClasses={['wide', 'nowrap', 'nowrap', 'nowrap']}
          data={rows}
        />
      );
    });

    return <div>
      <div style={{backgroundColor: "#FFFBCC"}} className="marginBottomL">
        This is very much a work-in-progress
      </div>
      {markup}
    </div>;
  }
});

export default BuildTestsPage;
