import React from 'react';

import { Grid } from 'es6!display/grid';
import { StatusDot, status_dots } from 'es6!display/changes/builds';
import SectionHeader from 'es6!display/section_header';
import ChangesPage from 'es6!display/page_chrome';
import APINotLoaded from 'es6!display/not_loaded';
import { TimeText, display_duration } from 'es6!display/time';

import * as api from 'es6!server/api';
import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

var TestHistoryPage = React.createClass({

  getInitialState: function() {
    return {
      info: null,
      history: null
    }
  },

  componentDidMount: function() {
    var project_id = this.props.projectUUID;
    var test_hash = this.props.testHash;

    var info_endpoint = `/api/0/projects/${project_id}/tests/${test_hash}/`;
    var history_endpoint = `/api/0/projects/${project_id}/tests/${test_hash}/history/` +
      '?per_page=100&branch=master';

    api.fetch(this, {
      info: info_endpoint,
      history: history_endpoint
    });
  },

  render() {
    if (!api.isLoaded(this.state.info)) {
      return <APINotLoaded state={this.state.info} />;
    }

    var history_content = this.renderHistory();
    
    return <ChangesPage>
      <SectionHeader>Builds in master</SectionHeader>
      {history_content}
    </ChangesPage>;
  },

  renderHistory() {
    if (!api.isLoaded(this.state.history)) {
      return <APINotLoaded 
        state={this.state.history}
        isInline={true}
      />;
    }

    var rows = _.map(this.state.history.getReturnedData(), t => {
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
      colnum={6}
      data={rows}
      headers={headers}
      cellClasses={cellClasses}
    />;
  }
});

export default TestHistoryPage;
