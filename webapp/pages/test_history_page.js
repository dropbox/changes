import React from 'react';

import Grid from 'es6!display/grid';
import { StatusDot, status_dots } from 'es6!display/builds';
import SectionHeader from 'es6!display/section_header';
import ChangesPage from 'es6!display/page_chrome';
import NotLoaded from 'es6!display/not_loaded';
import { TimeText, display_duration } from 'es6!display/time';

import { fetch_data } from 'es6!utils/data_fetching';
import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

var TestHistoryPage = React.createClass({

  getInitialState: function() {
    return {
      infoStatus: 'loading',
      infoData: null,
      infoError: {},

      historyStatus: 'loading',
      historyData: null,
      historyError: {},
    }
  },

  componentDidMount: function() {
    var project_id = this.props.projectUUID;
    var test_hash = this.props.testHash;

    var info_endpoint = `/api/0/projects/${project_id}/tests/${test_hash}/`;
    var history_endpoint = `/api/0/projects/${project_id}/tests/${test_hash}/history/` +
      '?per_page=100&branch=master';

    fetch_data(this, {
      info: info_endpoint,
      history: history_endpoint
    });
  },

  render: function() {
    if (this.state.infoStatus !== "loaded") {
      return <NotLoaded
        loadStatus={this.state.infoStatus}
        errorData={this.state.infoStatus}
      />;
    }

    var history_content = this.renderHistory();
    
    return <ChangesPage>
      <SectionHeader>Builds in master</SectionHeader>
      {history_content}
    </ChangesPage>;
  },

  renderHistory() {
    if (this.state.historyStatus !== "loaded") {
      return <NotLoaded 
        loadStatus={this.state.historyStatus}
        errorData={this.state.historyError}
        isInline={true}
      />;
    }

    var rows = _.map(this.state.historyData, t => {
      var build = t.job.build;
      var revision = build.source.revision;

      return [
        <StatusDot state={t.result.id} />,
        display_duration(t.duration / 1000),
        <a href="#">{utils.email_head(revision.author.email)}</a>,
        <a href="#">{utils.truncate(revision.sha, 8)}</a>,
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

    return <Grid
      data={rows}
      headers={headers}
      cellClasses={cellClasses}
    />;
  }
});

export default TestHistoryPage;
