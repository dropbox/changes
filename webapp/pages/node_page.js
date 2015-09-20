import React, { PropTypes } from 'react';

import SectionHeader from 'es6!display/section_header';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import { Grid } from 'es6!display/grid';
import { InfoList, InfoItem } from 'es6!display/info_list';
import { SingleBuildStatus } from 'es6!display/changes/builds';
import { TimeText } from 'es6!display/time';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';
import custom_content_hook from 'es6!utils/custom_content';

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
    var nodeID = this.props.nodeID;

    var detailsEndpoint = `/api/0/nodes/${nodeID}/`;
    var jobsEndpoint = `/api/0/nodes/${nodeID}/jobs/`;
    api.fetch(this, {
      nodeDetails: detailsEndpoint,
      nodeJobs: jobsEndpoint,
    })
  },

  render: function() {
    if (!api.allLoaded([this.state.nodeJobs, this.state.nodeDetails])) {
      return <APINotLoadedPage
        calls={[this.state.nodeJobs, this.state.nodeDetails]}
      />;
    }

    var node = this.state.nodeDetails.getReturnedData();
    utils.setPageTitle(node.name);

    var cellClasses = ['nowrap buildWidgetCell', 'nowrap', 'nowrap', 'wide', 'nowrap'];
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

    var extra_info_name = custom_content_hook('nodeInfoName'),
      extra_info_href = custom_content_hook('nodeInfo', null, details.name);

    var extra_indo_markup = null;
    if (extra_info_name && extra_info_href) {
      var extra_info_markup = <a 
        className="external inlineBlock"
        style={{marginTop: 3}}
        target="_blank"
        href={extra_info_href}>
        {extra_info_name}
      </a>;
    }

    return <ChangesPage>
      <SectionHeader>{details.name}</SectionHeader>
      <InfoList>
        <InfoItem label="Node ID">{details.id}</InfoItem>
        <InfoItem label="First Seen">
          <TimeText time={details.dateCreated} />
        </InfoItem>
      </InfoList>
      {extra_info_markup}
      <div className="marginBottomM marginTopM paddingTopS">
        Recent runs on this node
      </div>
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
