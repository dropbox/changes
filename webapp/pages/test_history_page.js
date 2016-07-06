import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesLinks from 'es6!display/changes/links';
import SectionHeader from 'es6!display/section_header';
import { AjaxError } from 'es6!display/errors';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import { ConditionDot,
         get_runnable_condition
 } from 'es6!display/changes/build_conditions';

import { ChangesChart } from 'es6!display/changes/charts';
import { Grid } from 'es6!display/grid';
import { TimeText, display_duration } from 'es6!display/time';
import SimpleTooltip from 'es6!display/simple_tooltip';
import { InfoList, InfoItem } from 'es6!display/info_list';


import InteractiveData from 'es6!pages/helpers/interactive_data';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

var TestHistoryPage = React.createClass({

  propTypes: {
    projectUUID: PropTypes.string.isRequired,
    testHash: PropTypes.string.isRequired,
  },

  getInitialState: function() {
    return {
      info: null,
      history: null
    }
  },

  componentWillMount: function() {
    var projectID = this.props.projectUUID;
    var testHash = this.props.testHash;

    var historyEndpoint = `/api/0/projects/${projectID}/tests/${testHash}/history/` +
      '?per_page=100&branch=master';

    this.setState({
      history: InteractiveData(this,
        'history',
        historyEndpoint),
    });
  },

  componentDidMount: function() {
    var projectID = this.props.projectUUID;
    var testHash = this.props.testHash;

    var info_endpoint = `/api/0/projects/${projectID}/tests/${testHash}/`;
    api.fetch(this, {
      info: info_endpoint,
    });

    this.state.history.initialize(InteractiveData.getParamsFromWindowUrl());
  },

  renderHistory() {
    var historyInteractive = this.state.history;

    if (historyInteractive.hasNotLoadedInitialData()) {
      return <APINotLoaded calls={historyInteractive.getDataToShow()} />;
    }

    var history = historyInteractive.getDataToShow().getReturnedData();

    var rows = _.map(history, t => {
      if (!t) {
        return [
          null, null, null, null, null,
          <i>Not run for this commit</i>,
          null
        ];
      }

      var build = t.job.build;
      var revision = build.source.revision;

      let dotText = '';
      const quarantined_results = ['quarantined_passed', 'quarantined_failed', 'quarantined_skipped'];
      if (_.contains(quarantined_results, t.result.id)) {
        dotText = 'Q';
      }
      var build_href = ChangesLinks.buildTestHref(build.id, t);
      return [
        <SimpleTooltip label={t.result.name} placement="right">
          <a className="buildStatus" href={build_href}>
            <ConditionDot condition={get_runnable_condition(t)} num={dotText} />
          </a>
        </SimpleTooltip>,
        display_duration(t.duration / 1000),
        t.numRetries,
        ChangesLinks.author(revision.author),
        ChangesLinks.phabCommit(revision),
        utils.first_line(revision.message),
        <TimeText time={revision.dateCommitted} />
      ];
    });

    let helpful_header = (text, help) => <SimpleTooltip label={help} placement="top">
                                            <span>{text}</span>
                                          </SimpleTooltip>;

    const retriesDoc = <div>Number of times the test was rerun to see if it would pass.<br/>
                         Passing tests should pass the first time and need no retries.</div>;
    var headers = [
      'Result',
      helpful_header('Duration', 'Reported run time of the test at this commit.'),
      helpful_header('Retries', retriesDoc),
      'Author',
      'Commit',
      'Name',
      'Committed'
    ];

    var cellClasses = ['buildWidgetCell', 'nowrap center', 'nowrap center', 'nowrap',
      'nowrap', 'wide', 'nowrap'];

    var errorMessage = null;
    if (historyInteractive.failedToLoadUpdatedData()) {
      errorMessage = <AjaxError response={historyInteractive.getDataForErrorMessage().response} />;
    }
    var style = historyInteractive.isLoadingUpdatedData() ? {opacity: 0.5} : null;

    var pagingLinks = historyInteractive.getPagingLinks();

    return <div style={style}>
      {errorMessage}
      <div style={{textAlign: "center"}}>
        <ChangesChart type="test" runnables={history} enableLatest={false} />
      </div>
      <Grid
        colnum={headers.length}
        data={rows}
        headers={headers}
        cellClasses={cellClasses}
      />
      <div className="marginTopM">
        {pagingLinks}
      </div>
    </div>;
  },

  render() {
    if (!api.isLoaded(this.state.info)) {
      return <APINotLoadedPage calls={this.state.info} />;
    }
    var test_data = this.state.info.getReturnedData();
    utils.setPageTitle(`${test_data.shortName} - History`);

    return <ChangesPage>
      <SectionHeader>History: {test_data.shortName}</SectionHeader>
      <InfoList className="marginTopM">
        <InfoItem label="Package">{test_data.package}</InfoItem>
      </InfoList>
      <br/>
      Displaying a list of the results of this test for every commit in master.
      <div className="marginTopM">
        {this.renderHistory()}
      </div>
    </ChangesPage>;
  }
});

export default TestHistoryPage;
