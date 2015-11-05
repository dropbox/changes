import React, { PropTypes } from 'react';
import moment from 'moment';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesLinks from 'es6!display/changes/links';
import SectionHeader from 'es6!display/section_header';
import SimpleTooltip from 'es6!display/simple_tooltip';
import { Grid } from 'es6!display/grid';
import { Menu1, MenuUtils } from 'es6!display/menus';
import { TimeText } from 'es6!display/time';

import ProjectPage from 'es6!pages/project_page/project_page';

import * as api from 'es6!server/api';

var TestsTab = React.createClass({

  propTypes: {
    // the project api response
    project: PropTypes.object,
    // flaky tests api response
    flakyTests: PropTypes.object,
    // quarantine tasks api response
    quarantineTasks: PropTypes.object,
    // the ProjectPage element
    pageElem: PropTypes.object.isRequired,
  },

  menuItems: [
    'Flaky Tests Dashboard',
    'Quarantine Task List',
  ],

  getInitialState: function() {
    return {
      selectedItem: 'Flaky Tests Dashboard',
    };
  },

  componentWillMount: function() {
    var queryParams = URI(window.location.href).search(true);

    // break with convention and use a query parameter here, since we already
    // use the hash for the overall tab
    var selectedScreen = MenuUtils.selectItemFromHash(
      '#' + queryParams['section'], this.menuItems);

    if (selectedScreen) {
      this.setState({ selectedItem: selectedScreen });
    }
  },

  componentDidMount: function() {
    var project = this.props.project.getReturnedData();
    // TODO: we could add date support...
    if (!api.allLoaded([this.props.flakyTests, this.props.quarantineTasks])) {
      api.fetch(this.props.pageElem, {
        flakyTests: `/api/0/projects/${project.id}/flaky_tests/`,
        quarantineTasks: '/api/0/quarantine_tasks'
      });
    }
  },

  render: function() {
    if (!api.allLoaded([this.props.flakyTests, this.props.quarantineTasks])) {
      return <APINotLoaded
        calls={[this.props.flakyTests, this.props.quarantineTasks]}
      />;
    }

    var InProgressMessage = <div className="messageBox marginBottomM">
      This tab is still a WIP (adding the ability for you to find tests via a
      filter, more dashboards, and other stuff.) Right now we have a flaky
      test dashboard finished.
    </div>;

    // render menu
    var selectedItem = this.state.selectedItem;

    var menu = <Menu1
      className="marginBottomM"
      items={this.menuItems}
      selectedItem={selectedItem}
      onClick={MenuUtils.onClickQueryParam(this, selectedItem, 'section')}
    />;

    var content = null;
    switch (selectedItem) {
      case 'Flaky Tests Dashboard':
        content = this.renderFlakyTests();
        break;
      case 'Quarantine Task List':
        content = this.renderQuarantineTasks();
        break;
      default:
        console.log(selectedItem);
        throw 'unreachable';
    }

    return <div>
      {InProgressMessage}
      {menu}
      {content}
    </div>;
  },

  renderFlakyTests() {
    var flakyTestsDict = this.props.flakyTests.getReturnedData();
    var date = flakyTestsDict.date;
    var flakyTests = flakyTestsDict.flakyTests;
  
    var data = _.map(flakyTests, test => {
      return [
        <div>
          {ChangesLinks.flaky_test_history(test)}{this.getQuarantineTasksForFlakyTest(test)}
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
        <SectionHeader>Flaky Tests ({date})</SectionHeader>
        <p>There were no flaky tests on this day.</p>
      </div>;
    }

    return <div>
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

  getQuarantineTasksForFlakyTest(test) {
    var ret = this.props.quarantineTasks.getReturnedData();
    if (!ret['fetched_data_from_phabricator']) {
      return null;
    }

    var linkedTasks = [];
    _.each(ret['tasks'], task => {
      if (task.description.indexOf(test.name) >= 0) {
        linkedTasks.push(task);
      }
    });

    if (_.isEmpty(linkedTasks)) {
      return null;
    }

    var markup = [];
    _.each(linkedTasks, (task, index) => {
      // TODO: use a better format than ISO8601
      var dateModified = moment.unix(task.dateModified).local().format(
        'ddd, MMMM Do YYYY, h:mm:ss a');

      var label = <div style={{textAlign: 'left'}}>
        <div>Assigned To: {this.assignedTo(task)}</div>
        <div>Last Modified: {dateModified}</div>
      </div>;

      markup.push(
        <SimpleTooltip label={label}>
          <a href={task.uri} target="_blank">
            {task.objectName}
          </a>
        </SimpleTooltip>
      );
      if (index < linkedTasks.length - 1) {
        markup.push(", ");
      }
    });

    return <span>{" ("}{markup}{")"}</span>;
  },

  renderQuarantineTasks() {
    // TODO: what I want to do is to show these inline next to tests on the
    // flaky dashboard. I don't have time, so instead I built the api call and
    // a simple way to see these tasks in one place. You who are reading this
    // should make this better.

    var project = this.props.project.getReturnedData();

    var ret = this.props.quarantineTasks.getReturnedData();
    if (!ret['fetched_data_from_phabricator']) {
      return <div>No data fetched from phabricator</div>;
    }
    var tasks = [];

    // Filter out tasks that aren't a part of this project (by looking for the
    // project slug in any contained url...)
    // TODO: do this serverside so we don't send a bunch of unneeded data?
    _.each(ret['tasks'], task => {
      var inProject = false;
      URI.withinString(task['description'], url => {
        var path = URI(url).path();
        if (path.indexOf(project.slug) >= 0) {
          inProject = true;
        }
        return url;
      });
      if (inProject) {
        tasks.push(task);
      }
    });

    tasks = _.sortBy(tasks, t => -1 * t.dateModified);

    var data = _.map(tasks, task => {
      var assignedTo = this.assignedTo(task);

      var style = {};
      if (task['status'] !== 'open') {
        style['textDecoration'] = 'line-through';
      };

      var taskMarkup = <SimpleTooltip label={task.statusName}>
        <a href={task.uri} className="subtle" style={style} target="_blank">
          [{task.objectName}]
          {" "}
          {task.title}
        </a>
      </SimpleTooltip>;

      return [
        assignedTo,
        taskMarkup,
        (task.dateModified - task.dateCreated > 60) ? 'Yes' : 'No',
        <TimeText format="X" time={task.dateModified} />
      ];
    });

    var cellClasses = [
      'nowrap',
      'wide easyClick',
      'nowrap',
      'nowrap'
    ];

    var explanation = 'Is dateUpdated more than 60 seconds later than ' +
      'dateCreated?';

    var headers = [
      'Assigned',
      'Task',
      <SimpleTooltip label={explanation} placement="left">
        <span>Ever Updated?</span>
      </SimpleTooltip>,
      'Modified'
    ];

    return <div>
      <div className="marginBottomL">
        This is a list of every task opened for a quarantined test within
        this project.
      </div>
      <Grid
        colnum={4}
        headers={headers}
        cellClasses={cellClasses}
        data={data}
      />
    </div>;
  },

  assignedTo(task) {
    var ret = this.props.quarantineTasks.getReturnedData();
    if (!ret['fetched_data_from_phabricator']) {
      return null;
    }
    var users = ret['users'];

    if (task.ownerPHID) {
      var assignedToDict = users[task.ownerPHID];
      return (assignedToDict && assignedToDict['name']) || 'unknown';
    }
    return null;
  }
});

export default TestsTab;
