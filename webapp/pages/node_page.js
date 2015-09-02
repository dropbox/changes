import React from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesPage from 'es6!display/page_chrome';
import { Grid } from 'es6!display/grid';
import { InfoList, InfoItem } from 'es6!display/info_list';
import { SingleBuildStatus } from 'es6!display/changes/builds';
import { TimeText } from 'es6!display/time';

import * as api from 'es6!server/api';

/**
 * Page that shows the builds associated with a single node, across all projects.
 */
var NodePage = React.createClass({

  getInitialState: function() {
    return {
      nodeJobs: null,
      nodeDetails: null,
    }
  },

  componentDidMount: function() {
    var nodeID = this.props.node_id;

    var detailsEndpoint = `/api/0/nodes/${nodeID}/`;
    var jobsEndpoint = `/api/0/nodes/${nodeID}/jobs/`;
    api.fetch(this, {
      nodeDetails: detailsEndpoint,
      nodeJobs: jobsEndpoint,
    })
  },

  render: function() {
    if (!api.mapIsLoaded(this.state, ['nodeJobs', 'nodeDetails'])) {
      return <APINotLoaded
        stateMap={this.state}
        stateMapKeys={['nodeJobs', 'nodeDetails']}
      />;
    }

    var cellClasses = ['nowrap', 'nowrap', 'nowrap', 'wide', 'nowrap'];
    var headers = [ 'Build', 'Phab.', 'Project', 'Name', 'Committed'];

    var grid_data = _.map(this.state.nodeJobs.getReturnedData(), d => {
      var project_href = "/v2/project/" + d.project.slug;
      return [
        <SingleBuildStatus build={d.build} parentElem={this} />,
        d.build.source.id.substr(0, 7),
        <a href={project_href}>{d.project.name}</a>,
        d.build.name,
        <TimeText time={d.build.dateCreated} />];
    })

    var details = this.state.nodeDetails.getReturnedData();
    return <ChangesPage>
      <InfoList style={{ margin: 10, marginLeft: 4 }}>
        <InfoItem label="Node ID">{details.id}</InfoItem>
        <InfoItem label="First Seen">
          <TimeText time={details.dateCreated} />
        </InfoItem>
      </InfoList>
      <Grid
        colnum={5}
        data={grid_data}
        cellClasses={cellClasses}
        headers={headers}
      />
    </ChangesPage>;
  }
});

export default NodePage;
