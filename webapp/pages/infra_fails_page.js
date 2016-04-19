import React from 'react';

import ChangesLinks from 'es6!display/changes/links';
import SectionHeader from 'es6!display/section_header';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import { Grid } from 'es6!display/grid';
import { SingleBuildStatus } from 'es6!display/changes/builds';
import { TimeText } from 'es6!display/time';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

/**
 * Page with information on recent infrastructural failures.
 */
var InfraFailsPage = React.createClass({

  getInitialState: function() {
    return {
      infraFailJobs: null,
    }
  },

  componentDidMount: function() {
    api.fetch(this, {
      infraFailJobs: `/api/0/admin_dash/infra_fail_jobs/`
    })
  },

  render: function() {
    if (!api.allLoaded([this.state.infraFailJobs])) {
      return <APINotLoadedPage
        calls={[this.state.infraFailJobs]}
      />;
    }

    utils.setPageTitle(`Infra fails`);

    var cellClasses = ['buildWidgetCell', 'nowrap', 'nowrap', 'wide easyClick', 'nowrap', 'nowrap'];
    var headers = [ 'Build', 'Project', 'Name', 'Message', 'Target', 'Started'];

    var data = this.state.infraFailJobs.getReturnedData();
    var grid_data = _.map(data['recent'], d => {
      return [
        <SingleBuildStatus build={d.build} parentElem={this} />,
        <div>{d.project.name}</div>,
        <div>{d.name}</div>,
        <a className="subtle" href={ChangesLinks.buildHref(d.build)}>
          {d.build.name}
        </a>,
        ChangesLinks.phab(d.build),
        <TimeText time={d.dateStarted} />];
    })

    return <ChangesPage>
      <SectionHeader>Recent Infra fails</SectionHeader>
      <div className="marginBottomM marginTopM paddingTopS">
        Jobs with infrastructural failures in the last 24 hours.
      </div>
      <Grid
        colnum={headers.length}
        data={grid_data}
        cellClasses={cellClasses}
        headers={headers}
      />
    </ChangesPage>;
  }
});

export default InfraFailsPage;
