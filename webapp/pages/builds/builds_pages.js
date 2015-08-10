import React from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesPage from 'es6!display/page_chrome';

import Sidebar from 'es6!pages/builds/sidebar';
import SingleBuild from 'es6!pages/builds/build_info';

import * as api from 'es6!server/api';

var cx = React.addons.classSet;

/*
 * The pages that show the results of builds run on a commit or diff. They're
 * just wrappers around BuildsPage
 */
// TODO: I need a page that just shows a single build, e.g. for arc test.

/**
 * Page that shows the builds associated with a single diff
 */
export var DiffPage = React.createClass({

  getInitialState: function() {
    return {
      diffBuilds: null,
    }
  },

  componentDidMount: function() {
    var diff_id = this.props.diff_id;
    api.fetch(this, {
      diffBuilds: `/api/0/phabricator_diffs/${diff_id}/builds`
    });
  },

  render: function() {
    if (!api.isLoaded(this.state.diffBuilds)) {
      return <APINotLoaded state={this.state.diffBuilds} isInline={false} />;
    }
    var diff_data = this.state.diffBuilds.getReturnedData();

    // emergency backups in case phabricator is unreachable
    diff_data['revision_id'] = diff_data['revision_id'] || this.props.diff_id.substr(1);
    diff_data['dateCreated'] = diff_data['dateCreated'] || 0; // unix timestamp

    var builds = _.chain(diff_data.changes)
      .pluck('builds')
      .flatten()
      .value();

    return <BuildsPage
      type="diff"
      targetData={diff_data}
      builds={builds}
    />;
  }
});

/**
 * Page that shows the builds associated with a single commit
 */
export var CommitPage = React.createClass({

  getInitialState: function() {
    return {
      commitBuilds: null,
      source: null,
    }
  },

  componentDidMount: function() {
    var uuid = this.props.sourceUUID;

    api.fetch(this, {
      commitBuilds: `/api/0/sources/${uuid}/builds`,
      source: `/api/0/sources/${uuid}`
    });
  },

  render: function() {
    var slug = this.props.project;

    if (!api.mapIsLoaded(this.state, ['commitBuilds', 'source'])) {
      return <APINotLoaded
        isInline={false}
        stateMap={this.state}
        stateMapKeys={['commitBuilds', 'source']}
      />;
    }

    return <BuildsPage
      type="commit"
      targetData={this.state.source.getReturnedData()}
      builds={this.state.commitBuilds.getReturnedData()}
    />;
  }
});

/** ---IMPLEMENTATION--- **/

/**
 * The internal page shared by CommitPage and DiffPage (since the logic is
 * basically the same)
 */
var BuildsPage = React.createClass({

  propTypes: {
    // are we rendering for a diff or a commit
    type: React.PropTypes.oneOf(['diff', 'commit']).isRequired,
    // info about the commit (a changes source object) or diff (from phab.)
    targetData: React.PropTypes.object,
    // the builds associated with this diff/commit. They may be more sparse
    // than a call to build_details...we use this to populate the sidebar
    builds: React.PropTypes.array.isRequired,
  },

  getInitialState: function() {
    var query_params = URI(window.location.href).search(true);

    return {
      activeBuildID: query_params.buildID,
      tests: {}, // fetched on demand
    }
  },

  render: function() {
    var content_style = {
      marginLeft: 300,
      paddingRight: 10
    };

    this.updateWindowUrl();

    // TODO: cleanup!
    // padding: "10px 35px",
    return <ChangesPage bodyPadding={false} fixed={true}>
      <Sidebar
        builds={this.props.builds}
        type={this.props.type}
        targetData={this.props.targetData}
        activeBuildID={this.state.activeBuildID}
        pageElem={this}
      />
      <div style={{paddingTop: 32}}>
        <div style={content_style} >
          {this.getContent()}
        </div>
      </div>
    </ChangesPage>;
  },

  updateWindowUrl: function() {
    var query_params = URI(window.location.href).search(true);
    if (this.state.activeBuildID &&
        this.state.activeBuildID !== query_params['buildID']) {
      query_params['buildID'] = this.state.activeBuildID;
      window.history.replaceState(
        null,
        'changed tab',
        URI(window.location.href)
          .search(query_params)
          .toString()
      );
    }
  },

  getContent: function() {
    var builds = this.props.builds;

    if (this.state.activeBuildID) {
      var build = _.filter(builds, b => b.id === this.state.activeBuildID);
      if (build) {
        // use a key so that we remount when switching builds
        return {
          [ build[0].id ]:
            <SingleBuild
              build={build[0]}
            />
        };
      }
    }

    // get all builds for latest code
    var latest_builds = builds;

    if (this.props.type === 'diff') {
      var builds_by_diff_id = _.groupBy(
        builds,
        b => b.source.data['phabricator.diffID']);

      var latest_diff_id = _.chain(builds)
        .keys()
        .sortBy()
        .last()
        .value();

      latest_builds = builds_by_diff_id[latest_diff_id];
    }

    return _.map(latest_builds, b => <SingleBuild build={b} />);
  }
});
