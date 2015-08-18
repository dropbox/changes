import React from 'react';

import ChangesPage from 'es6!display/page_chrome';
import SectionHeader from 'es6!display/section_header';

import APINotLoaded from 'es6!display/not_loaded';
import DisplayUtils from 'es6!display/changes/utils';
import { AjaxError } from 'es6!display/errors';
import { BuildWidget, get_build_cause } from 'es6!display/changes/builds';
import { Grid } from 'es6!display/grid';
import { TimeText } from 'es6!display/time';

import DataControls from 'es6!pages/helpers/data_controls';

import * as api from 'es6!server/api';

var BuildsPage = React.createClass({

  componentWillMount: function() {
    this.setState({
      buildsControls: DataControls(
        this,
        'buildsControls',
        '/api/0/authors/me/builds/')
    });
  },

  componentDidMount: function() {
    if (!this.state.buildsControls.hasRunInitialize()) {
      this.state.buildsControls.initialize({});
    }
  },

  render: function() {
   var controls = this.state.buildsControls;

    if (controls.hasNotLoadedInitialData()) {
      return <APINotLoaded
        state={controls.getDataToShow()}
        isInline={true}
      />;
    }

    var data_to_show = controls.getDataToShow();

    var data = _.map(data_to_show.getReturnedData(), build => {
      var target = null;
      if (_.contains(build.tags, 'arc test')) {
        target = '';
      } else if (build.source.patch) {
        target = <a
          className="external"
          href={build.source.data['phabricator.revisionURL']}
          target="_blank">
          {'D' + build.source.data['phabricator.revisionID']}
        </a>
      } else {
        target = build.source.revision.sha.substr(0, 7);
      }

      return [
        <BuildWidget build={build} parentElem={this} />,
        target,
        DisplayUtils.authorLink(build.author),
        build.name,
        get_build_cause(build),
        <TimeText time={build.dateStarted} />
      ];
    });

    var cellClasses = ['buildWidgetCell', 'nowrap', 'nowrap', 'wide', 'nowrap', 'nowrap'];

    var headers = [
      'Result',
      'Target',
      'By',
      'Name',
      'Cause',
      'Started'
    ];

    var error_message = null;
    if (controls.failedToLoadUpdatedData()) {
      error_message = <AjaxError response={controls.getDataForErrorMessage().response} />;
    }

    var style = controls.isLoadingUpdatedData() ? {opacity: 0.5} : null;

    return <ChangesPage>
      {error_message}
      <SectionHeader className="inline">My Builds</SectionHeader>
      <div style={style}>
        <Grid
          colnum={6}
          cellClasses={cellClasses}
          data={data}
          headers={headers}
        />
      {this.renderPagination()}
      </div>
    </ChangesPage>;
  },

  renderPagination: function(builds) {
    var links = this.state.buildsControls.getPaginationLinks();
    return <div className="marginTopM marginBottomM">{links}</div>;
  },
});

export default BuildsPage;
