import React, { PropTypes } from 'react';

import ChangesLinks from 'es6!display/changes/links';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import { Error } from 'es6!display/errors';
import { get_build_cause } from 'es6!display/changes/builds';

import Sidebar from 'es6!pages/builds/sidebar';
import { SingleBuild, LatestBuildsSummary } from 'es6!pages/builds/build_info';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

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
      return <APINotLoadedPage calls={this.state.diffBuilds} />;
    }
    var diff_data = this.state.diffBuilds.getReturnedData();
    // Note: if the "fetched_data_from_phabricator" key is false, we weren't
    // able to reach phabricator. We still have builds data that we want to
    // render...just do our best to deal with the missing phabricator data.

    // TODO: delete
    diff_data['fetched_data_from_phabricator'] = true;

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

    if (!api.allLoaded([this.state.commitBuilds, this.state.source])) {
      return <APINotLoadedPage
        calls={[this.state.commitBuilds, this.state.source]}
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
    type: PropTypes.oneOf(['diff', 'commit']).isRequired,
    // info about the commit (a changes source object) or diff (from phab.)
    targetData: PropTypes.object,
    // the builds associated with this diff/commit. They may be more sparse
    // than a call to build_details...we use this to populate the sidebar
    builds: PropTypes.array.isRequired,
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
      marginLeft: 310,
      padding: 20
    };

    this.updateWindowUrl();

    // TODO: cleanup!
    return <ChangesPage bodyPadding={false} fixed={true}>
      <div className="buildsLabelHeader">
        {this.renderLabelHeader()}
      </div>
      <div className="persistentMessageHeader" style={{position: 'fixed', top: 40, zIndex: 20}}>
        You probably came here from clicking a link in Phabricator. This is
        still not quite ready for primetime (I added the Phabricator extension
        a bit early), but you{"'"}re welcome to test and email us feedback
        (we'll add a feedback link to the header soon too.)
      </div>
      <Sidebar
        builds={this.props.builds}
        type={this.props.type}
        targetData={this.props.targetData}
        activeBuildID={this.state.activeBuildID}
        pageElem={this}
      />
      <div style={{paddingTop: 150}}>
        <div style={content_style} >
          {this.getErrorMessage()}
          {this.getContent()}
        </div>
      </div>
    </ChangesPage>;
  },

  updateWindowUrl: function() {
    var query_params = URI(window.location.href).search(true);
    if (this.state.activeBuildID !== query_params['buildID']) {
      query_params['buildID'] = this.state.activeBuildID;
      window.history.replaceState(
        null,
        'changed tab',
        URI(window.location.href)
          .search(_.pick(query_params, value => !!value))
          .toString()
      );
    }
  },

  getErrorMessage: function() {
    if (this.props.type === 'diff') {
      var diff_data = this.props.targetData;
      if (!diff_data["fetched_data_from_phabricator"]) {
        return <Error className="marginBottomM">
          Unable to get diff data from Phabricator!
        </Error>;
      }
    }
    return null;
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

      var latest_diff_id = _.chain(builds_by_diff_id)
        .keys()
        .sortBy()
        .last()
        .value();

      latest_builds = builds_by_diff_id[latest_diff_id];
    }

    return <LatestBuildsSummary
      builds={latest_builds} 
      type={this.props.type}
      targetData={this.props.targetData}
      pageElem={this}
    />;
  },

  renderLabelHeader: function() {
    var type = this.props.type;

    var header = "No header yet";
    if (type === 'commit') {
      var source = this.props.targetData;
      var authorLink = ChangesLinks.author(source.revision.author, true);
      var commitLink = ChangesLinks.phabCommitHref(source.revision);

      header = <div>
        <a className="subtle" href={commitLink} target="_blank">
          {source.revision.sha.substring(0,7)}
        </a>
        {": "}
        {utils.first_line(source.revision.message)}
        {" (by "}
        {authorLink}
        {")"}
      </div>;
    } else if (type === 'diff') {
      var diff_data = this.props.targetData;
      var authorLink = ChangesLinks.author(
        this.getAuthorForDiff(this.props.builds), true);
      header = <div>
        <a className="subtle" href={diff_data.uri} target="_blank">
          D{diff_data.id}
        </a>
        {": "}
        {diff_data.title}
        {" (by "}
        {authorLink}
        {")"}
      </div>;
    } else {
      throw 'unreachable';
    }

    return header;
  },

  getAuthorForDiff: function(builds) {
    // TODO: the author of any cause=phabricator build for a diff is always the
    // same as the author of the diff. Display them here
    var author = null;
    _.each(builds, b => {
      if (get_build_cause(b) === 'phabricator') {
        author = b.author;
      }
    });
    return author;
  }
});

export var SingleBuildPage = React.createClass({

  getInitialState: function() {
    return {
      build: null
    };
  },

  componentDidMount: function() {
    api.fetch(this, {
      build: `/api/0/builds/${this.props.buildID}`
    });
  },

  render: function() {
    if (!api.isLoaded(this.state.build)) {
      return <APINotLoadedPage calls={this.state.build} />;
    }

    return <ChangesPage>
      <SingleBuild build={this.state.build.getReturnedData()} />
    </ChangesPage>;
  },
});
