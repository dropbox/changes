import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import SectionHeader from 'es6!display/section_header';
import { Grid } from 'es6!display/grid';

import ProjectPage from 'es6!pages/project_page/project_page';

import * as api from 'es6!server/api';

var TestsTab = React.createClass({

  propTypes: {
    // the project api response
    project: PropTypes.object,
    // flaky tests api response
    flakyTests: PropTypes.object,
    // the ProjectPage element
    pageElem: PropTypes.object.isRequired,
  },

  getInitialState: function() {
    return {};
  },

  componentDidMount: function() {
    var project = this.props.project.getReturnedData();
    // TODO: we could add date support...
    api.fetch(this.props.pageElem, {
      flakyTests: `/api/0/projects/${project.id}/flaky_tests/`
    });
  },

  render: function() {
    if (!api.isLoaded(this.props.flakyTests)) {
      return <APINotLoaded calls={this.props.flakyTests} />;
    }

    var InProgressMessage = <div className="messageBox marginBottomL">
      This tab is still a WIP (adding the ability for you to find tests via a
      filter, more dashboards, and other stuff.) Right now we have a flaky
      test dashboard finished.
    </div>;

    var flakyTestsDict = this.props.flakyTests.getReturnedData();
    var date = flakyTestsDict.date;
    var flakyTests = flakyTestsDict.flakyTests;
  
    var data = _.map(flakyTests, test => {
      return [
        <div>
          {test.short_name}
          <div className="subText">{test.name}</div>
        </div>,
        test.double_reruns,
        <span>
          {test.flaky_runs}
          {" ("}
          {(100 * test.flaky_runs / test.passing_runs).toFixed(2)}
          {"%)"}
        </span>
      ];
    });

    if (!flakyTests.length) {
      return <div>
        {InProgressMessage}
        <SectionHeader>Flaky Tests ({date})</SectionHeader>
        <p>There were no flaky tests on this day.</p>
      </div>;
    }

    return <div>
      {InProgressMessage}
      <SectionHeader>Flaky Tests ({date})</SectionHeader>
      <p>
        A test is called flaky if its first run failed, but some of its reruns
        passed.  The goal of this page is to show the flakiest tests of this
        project so engineers can investigate why they are flaky and fix them.
      </p>
      <p>
        We store and show up to 200 flaky tests per day.
      </p>
      <Grid
        colnum={3}
        headers={['Test', 'Double Flakes', 'Flaky Runs (% passing)']}
        cellClasses={['wide', 'nowrap', 'nowrap']}
        data={data}
      />
    </div>;
  },
});

export default TestsTab;
