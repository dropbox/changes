import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import SectionHeader from 'es6!display/section_header';
import { AjaxError } from 'es6!display/errors';
import { ChangesPage } from 'es6!display/page_chrome';
import { Grid, GridRow } from 'es6!display/grid';
import { Tabs, MenuUtils } from 'es6!display/menus';

import InteractiveData from 'es6!pages/helpers/interactive_data';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

var BuildTestsPage = React.createClass({

  menuItems: [
    'Not Passing Tests',
    'Slow Tests',
  ],

  getInitialState: function() {
    return {
      selectedItem: null, // set in componentWillMount

      expandedTests: {},
      expandedTestsData: {}
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
    });
  },

  componentDidMount: function() {
    _.each([['slowTests', 'Slow Tests']], tabs => {
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
      return <APINotLoaded state={this.state.buildInfo} />;
    }
    var buildInfo = this.state.buildInfo.getReturnedData();

    // render menu
    var selectedItem = this.state.selectedItem;

    var menu = <Tabs
      items={this.menuItems}
      selectedItem={selectedItem}
      onClick={MenuUtils.onClick(this, selectedItem)}
    />;

    var content = null;
    switch (selectedItem) {
      case 'Not Passing Tests':
        content = this.renderFailed();
        break;
      case 'Slow Tests':
        content = this.renderSlow();
        break;
      // TODO: slow test files
      default:
        throw 'unreachable';
    }

    var name = buildInfo.project.name;
    return <ChangesPage highlight="Projects">
      <SectionHeader>Tests for {name} Build</SectionHeader>
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
      return <div>No tests failed</div>;
    }

    var project_id = this.state.buildInfo.getReturnedData().project.id;

    var rows = [];
    _.each(failedTests, test => {
      var href = `/v2/project_test/${project_id}/${test.hash}`;

      var onClick = __ => {
        this.setState(
          utils.update_key_in_state_dict('expandedTests',
            test.test_id,
            !this.state.expandedTests[test.test_id])
        );

        if (!this.state.expandedTestsData[test.test_id]) {
          api.fetchMap(this, 'expandedTestsData', {
            [ test.test_id ]: `/api/0/tests/${test.test_id}/`
          });
        }
      };

      var markup = [
        <div>
          {test.shortName} <a onClick={onClick}>Expand</a>
          <div className="subText">{test.name}</div>
        </div>
      ];

      rows.push([
        markup,
        <a href={href}>History</a>,
      ]);

      if (this.state.expandedTests[test.test_id]) {
        if (!api.isLoaded(this.state.expandedTestsData[test.test_id])) {
          rows.push(GridRow.oneItem(
            <APINotLoaded
              className="marginTopM"
              calls={this.state.expandedTestsData[test.test_id]}
            />
          ));
        } else {
          var data = this.state.expandedTestsData[test.test_id].getReturnedData();
          rows.push(GridRow.oneItem(
            <div className="marginTopS">
              <b>Captured Output</b>
              <pre className="defaultPre">
              {data.message}
              </pre>
            </div>
          ));
        }
      }
    });

    var tests_by_result = _.groupBy(failedTests, t => t.result);
    var result_markup = _.map(tests_by_result, (tests, result) => {
      var sentence = utils.plural(tests.length, "test(s) " + result);
      var rest_of_words = _.rest(sentence.split(" ")).join(" ");

      return <div className="marginTopS">
        <span className="lb">{tests.length}</span>
        {" "}
        {rest_of_words}
      </div>;
    });

    return <div>
      {result_markup}
      <Grid
        colnum={2}
        className="marginBottomM marginTopM"
        data={rows}
        headers={['Name', 'Links']}
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
});

export default BuildTestsPage;
