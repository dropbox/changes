import React, { PropTypes } from 'react';

import ChangesLinks from 'es6!display/changes/links';
import SectionHeader from 'es6!display/section_header';
import { AjaxError } from 'es6!display/errors';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import { Grid } from 'es6!display/grid';
import { SingleBuildStatus, get_build_cause } from 'es6!display/changes/builds';
import { TimeText } from 'es6!display/time';

import InteractiveData from 'es6!pages/helpers/interactive_data';

var MyBuildsPage = React.createClass({

  componentWillMount: function() {
    this.setState({
      buildsInteractive: InteractiveData(
        this,
        'buildsInteractive',
        '/api/0/authors/me/builds/')
    });
  },

  componentDidMount: function() {
    if (!this.state.buildsInteractive.hasRunInitialize()) {
      this.state.buildsInteractive.initialize({});
    }
  },

  render: function() {
   var interactive = this.state.buildsInteractive;

    if (interactive.hasNotLoadedInitialData()) {
      return <APINotLoadedPage
        calls={interactive.getDataToShow()}
      />;
    }

    var data_to_show = interactive.getDataToShow();

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
        target = ChangesLinks.phabCommit(build.source.revision);
      }

      return [
        <SingleBuildStatus build={build} parentElem={this} />,
        target,
        ChangesLinks.author(build.author),
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
    if (interactive.failedToLoadUpdatedData()) {
      error_message = <AjaxError response={interactive.getDataForErrorMessage().response} />;
    }

    var style = interactive.isLoadingUpdatedData() ? {opacity: 0.5} : null;

    return <ChangesPage>
      {error_message}
      <SectionHeader>My Builds</SectionHeader>
      <div style={style}>
        <Grid
          colnum={6}
          cellClasses={cellClasses}
          data={data}
          headers={headers}
        />
      {this.renderPaging()}
      </div>
    </ChangesPage>;
  },

  renderPaging: function(builds) {
    var links = this.state.buildsInteractive.getPagingLinks();
    return <div className="marginTopM marginBottomM">{links}</div>;
  },
});

export default MyBuildsPage;
