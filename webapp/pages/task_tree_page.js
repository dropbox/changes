import React, { PropTypes } from 'react';

import ChangesLinks from 'es6!display/changes/links';
import SectionHeader from 'es6!display/section_header';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import { Grid } from 'es6!display/grid';
import { SingleBuildStatus } from 'es6!display/changes/builds';
import { TimeText } from 'es6!display/time';
import SimpleTooltip from 'es6!display/simple_tooltip';


import { get_runnable_condition, ConditionDot } from 'es6!display/changes/build_conditions';


import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

/**
 * TaskTreePage renders the task tree for an object id, indicating the state and type of
 * all tasks. This is intended as a debugging aide.
 * Note that task trees can been deep and require many queries to generate, so this UI should be
 * used with care, and probably not while we're having major load issues.
 */
var TaskTreePage = React.createClass({

  getInitialState: function() {
    return {
      objectTasks: null,
    }
  },

  componentDidMount: function() {
    var objectID = this.props.objectID;

    api.fetch(this, {
      objectTasks: `/api/0/tasks/?object_id=${objectID}`,
    })
  },

  render: function() {
    if (!api.allLoaded([this.state.objectTasks])) {
      return <APINotLoadedPage
        calls={[this.state.objectTasks]}
      />;
    }

    utils.setPageTitle(`Task tree dump`);

    var data = this.state.objectTasks.getReturnedData();

    let tasks = [];
    _.each(data, d => {
         tasks.push(<li key={d['id']}><TaskTree taskID={d['id']}/></li>);
    });

    let content = <ul>{tasks}</ul>;
    if (data.length == 0) {
       content = <div>No tasks found; they may have been cleaned up, or the supplied id may be invalid.</div>;
    }
    return <ChangesPage>
        <SectionHeader>Task Tree for {this.props.objectID}</SectionHeader>
        {content}
    </ChangesPage>;
  }
});

var TaskTree = React.createClass({

  propTypes: {
       taskID: PropTypes.string,
  },

  getInitialState: function() {
    return {
      taskTree: null,
    }
  },

  componentDidMount: function() {
    api.fetch(this, {
      taskTree: `/api/0/tasks/${this.props.taskID}/`,
    })
  },

  renderTasks: function(t) {
     let kids = null;
     if (t.children) {
       let kidlist = _.map(t.children, d => {
          return <li key={d.id}>{this.renderTasks(d)}</li>;
       });
       kids = <ul>{kidlist}</ul>;
    }
    let args = JSON.stringify(t.args);
    let name = <SimpleTooltip label={args}><span>{t.name}</span></SimpleTooltip>;
    return <span><div><ConditionDot condition={get_runnable_condition(t)} size='smaller'/>
       {name} <i style={{color: 'gray'}}>[modified {moment.utc(t.dateModified).fromNow()}]</i></div>
    {kids}
    </span>;
   },

  render: function() {
    if (!api.allLoaded([this.state.taskTree])) {
      return <APINotLoadedPage
        calls={[this.state.taskTree]}
      />;
    }
    let data = this.state.taskTree.getReturnedData();
    return <div>{this.renderTasks(data)}</div>;
  },

});

export default TaskTreePage;
