import React from 'react';

import Grid from 'es6!display/grid';
import { StatusDot, status_dots } from 'es6!display/builds';
import SectionHeader from 'es6!display/section_header';
import ChangesPage from 'es6!display/page_chrome';
import NotLoaded from 'es6!display/not_loaded';
import { TimeText } from 'es6!display/time';

import { fetch_data } from 'es6!utils/data_fetching';
import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

var AllProjectsPage = React.createClass({

  getInitialState: function() {
    return {
      projectsStatus: 'loading',
      projectsData: null,
      projectsError: {},
    }
  },

  componentDidMount: function() {
    var projects_endpoint = '/api/0/projects';

    fetch_data(this, {
      projects: projects_endpoint,
    });
  },

  render: function() {
    if (this.state.projectsStatus !== "loaded") {
      return <NotLoaded
        loadStatus={this.state.projectsStatus}
        errorData={this.state.projectsError}
      />;
    }

    var grid_data = _.map(this.state.projectsData, p => {
      var status_dot = null;
      if (p.lastBuild) {
        var status_dot = <StatusDot
          result={p.lastBuild.result.id}
        />;
      }

      return [
        status_dot,
        <a href={"/v2/project/" + p.slug}>{p.name}</a>
      ];
    });
    
    var headers = ['Status', 'Name'];
    var cellClasses = ['nowrap', 'wide'];

    return <ChangesPage>
      <SectionHeader>All Projects</SectionHeader>
      <Grid data={grid_data} headers={headers} cellClasses={cellClasses} />
    </ChangesPage>;
  }
});

export default AllProjectsPage;
