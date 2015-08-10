import React from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import DisplayUtils from 'es6!display/changes/utils';
import { AjaxError } from 'es6!display/errors';
import { BuildWidget, get_build_cause } from 'es6!display/changes/builds';
import { Grid } from 'es6!display/grid';
import { Menu1 } from 'es6!display/menus';
import { TimeText } from 'es6!display/time';

import DataControls from 'es6!pages/helpers/data_controls';

import * as api from 'es6!server/api';

var BuildsTab = React.createClass({

  propTypes: {
    // the project api response
    project: React.PropTypes.object,

    // state is handled by parent so that its preserved if someone selects
    // another tab
    myState: React.PropTypes.object,

    // The datacontrols object that handles dealing with data
    controls: React.PropTypes.object,

    // parent elem that has state
    pageElem: React.PropTypes.element.isRequired,
  },

  statics: {
    getEndpoint: function(slug) {
      return `/api/0/projects/${slug}/builds/`;
    }
  },

  componentDidMount: function() {
    if (!this.props.controls.hasRunInitialize()) {
      var params = this.props.isInitialTab ? DataControls.getParamsFromWindowUrl() : null;
      params = params || {};

      this.props.controls.initialize(params || {});
    }

    // if this table has data to render, let's make sure the window url is
    // correct
    if (api.isLoaded(this.props.controls.getDataToShow())) {
      this.props.controls.updateWindowUrl();
    }
  },

  render: function() {
    var controls = this.props.controls;

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
        <BuildWidget build={build} />,
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

    return <div>
      {this.renderControls()}
      {error_message}
      <div style={style}>
        <Grid
          colnum={6}
          cellClasses={cellClasses}
          data={data}
          headers={headers}
        />
      </div>
      {this.renderPagination()}
    </div>;
  },

  renderControls: function(commits) {
    var items = [
      'All',
      'Commits Only',
      'Diffs/arc test only'
    ];

    var params_for_items = {
      'All': {
        'include_patches': 1,
        'patches_only': 0
      },
      'Commits Only': {
        'include_patches': 0,
        'patches_only': 0
      },
      'Diffs/arc test only': {
        'include_patches': 1,
        'patches_only': 1
      }
    };

    var current_params = this.props.controls.getCurrentParams();
    var selected_item = 'All';
    _.each(params_for_items, (params, item) => {
      var is_selected = true;
      _.each(params, (v,k) => {
        if (current_params[k]+"" !== v+"") {
          is_selected = false;
        }
      });
      if (is_selected) {
        selected_item = item;
      }
    });

    var onclick = item => this.props.controls.updateWithParams(params_for_items[item], true);

    return <Menu1
      className="marginBottomS"
      items={items}
      selectedItem={selected_item}
      onClick={onclick}
    />;
  },

  renderPagination: function(commits) {
    var links = this.props.controls.getPaginationLinks();
    return <div className="marginTopM marginBottomM">{links}</div>;
  },
});

var TODO = React.createClass({
  render: function() {
    return <div>TODO</div>;
  }
});

export default BuildsTab;
