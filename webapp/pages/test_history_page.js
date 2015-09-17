import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesLinks from 'es6!display/changes/links';
import SectionHeader from 'es6!display/section_header';
import { AjaxError } from 'es6!display/errors';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import { ConditionDot } from 'es6!display/changes/builds';
import { Grid } from 'es6!display/grid';
import { TimeText, display_duration } from 'es6!display/time';

import InteractiveData from 'es6!pages/helpers/interactive_data';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

var TestHistoryPage = React.createClass({

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

  render() {
    if (!api.isLoaded(this.state.info)) {
      return <APINotLoadedPage calls={this.state.info} />;
    }

    return <ChangesPage>
      <SectionHeader>Commits in master</SectionHeader>
      <div className="marginTopM">
        {this.renderHistory()}
      </div>
    </ChangesPage>;
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
          null, null, null, null, 
          <i>Not run for this commit</i>, 
          null
        ];
      }

      var build = t.job.build;
      var revision = build.source.revision;

      return [
        <ConditionDot condition={t.result.id} />,
        display_duration(t.duration / 1000),
        ChangesLinks.author(revision.author),
        ChangesLinks.phabCommit(revision),
        utils.first_line(revision.message),
        <TimeText time={revision.dateCreated} />
      ];
    });

    var headers = [
      'Result',
      'Duration',
      'Author',
      'Commit',
      'Name',
      'Committed'
    ];

    var cellClasses = ['nowrap center', 'nowrap center', 'nowrap',
      'nowrap', 'wide', 'nowrap'];

    var errorMessage = null;
    if (historyInteractive.failedToLoadUpdatedData()) {
      errorMessage = <AjaxError response={historyInteractive.getDataForErrorMessage().response} />;
    }
    var style = historyInteractive.isLoadingUpdatedData() ? {opacity: 0.5} : null;

    var pagingLinks = historyInteractive.getPagingLinks();

    return <div style={style}>
      {errorMessage}
      <Grid
        colnum={6}
        data={rows}
        headers={headers}
        cellClasses={cellClasses}
      />
      <div className="marginTopM">
        {pagingLinks}
      </div>
    </div>;
  }
});

export default TestHistoryPage;
