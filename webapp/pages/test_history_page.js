import React from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesPage from 'es6!display/page_chrome';
import SectionHeader from 'es6!display/section_header';
import { Grid } from 'es6!display/grid';
import { StatusDot } from 'es6!display/changes/builds';
import { TimeText, display_duration } from 'es6!display/time';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

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
      <SectionHeader>Commits in master</SectionHeader>
      <div className="marginTopM">
        {history_content}
      </div>
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
