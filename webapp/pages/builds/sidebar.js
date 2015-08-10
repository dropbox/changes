import React from 'react';
import moment from 'moment';

import { TimeText, display_duration } from 'es6!display/time';
import { get_build_state, get_build_cause } from 'es6!display/changes/builds';

import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

/*
 * The sidebar on the builds page. Shows a list of builds for a single diff or
 * commit
 */

var Sidebar = React.createClass({

  propTypes: {
    // list of builds to render in side bar
    builds: React.PropTypes.array,

    // are we rendering for a diff or a commit
    type: React.PropTypes.oneOf(['diff', 'commit']),

    // if its a diff, grab its information
    targetData: React.PropTypes.object,

    // which build are we currently showing, if any
    activeBuildID: React.PropTypes.string,

    // the parent page element. Sidebar clicks change its state
    pageElem: React.PropTypes.element,
  },

  render: function() {
    return <div className="buildsSidebar">
      {this.renderHeader()}
      {this.renderBuildsList()}
      {this.renderSurroundingBuilds()}
      {this.renderOtherActions()}
    </div>;
  },

  renderHeader: function() {
    var type = this.props.type;

    var header = "No header yet";
    if (type === 'commit') {
      var source = this.props.targetData;
      header = <div>
        {source.revision.sha.substring(0,7)}{": "}
        {utils.first_line(source.revision.message)}
      </div>;
    } else if (type === 'diff') {
      var diff_data = this.props.targetData;
      header = <div>
        <a className="subtle" href={diff_data.uri} target="_blank">
          D{diff_data.id}
        </a>
        {": "}
        {diff_data.title}
      </div>;
    } else {
      throw 'unreachable';
    }

    return <div style={{fontWeight: 'bold', padding: 10}}>
      {header}
    </div>;
  },

  renderBuildsList: function() {
    var type = this.props.type;

    var content = "No content yet";
    if (type === 'commit') {
      content = this.renderBuildsForCommit();
    } else if (type === 'diff') {
      content = this.renderBuildsForDiff();
    } else {
      throw 'unreachable';
    }

    return <div>
      {content}
    </div>;
  },

  renderBuildsForCommit: function() {
    var builds = this.props.builds,
      source = this.props.targetData;

    console.log(source);
    var label = <span>
      Committed {"("}<TimeText time={source.revision.dateCommitted} />{")"}
    </span>;
    var content = this.renderBuilds(builds);

    return this.renderSection(label, content);
  },

  renderBuildsForDiff: function() {
    // the main difference between diffs and commits is that diffs may have
    // multiple, distinct code changes, each of which have their own builds.
    // We want one section for each diff update
    var builds = this.props.builds,
      diff_data = this.props.targetData;

    var builds_by_update = _.groupBy(builds, b => b.source.data['phabricator.diffID']);

    var all_diff_ids = _.sortBy(diff_data.diffs).reverse();
    // one of those diff updates is the original diff that was sent
    var original_single_diff_id = _.last(all_diff_ids);

    var sections = [];
    _.each(all_diff_ids, (single_diff_id, index) => {
      var builds = builds_by_update[single_diff_id];
      var changes_data = diff_data.changes[single_diff_id];

      var diff_update_num = all_diff_ids.length - index - 1;

      if (single_diff_id > original_single_diff_id) {
        if (changes_data) {
          var section_header = <span>
            Diff Update #{diff_update_num}
            {" ("}
            <TimeText time={moment.utc(changes_data['dateCreated'])} />
            {")"}
          </span>;
        } else {
          var section_header = <span>Diff Update #{diff_update_num}</span>
        }
      } else {
        var section_header = <span>
          Created D{diff_data.id}{" ("}
          <TimeText time={moment.unix(diff_data.dateCreated).toString()} />
          {")"}
        </span>;
      }
      var section_content = builds ? this.renderBuilds(builds) : null;

      sections.push(this.renderSection(section_header, section_content));
    });
    return sections;
  },

  renderBuilds: function(builds) {
    if (builds === undefined) {
      return null;
    }
    builds = _.chain(builds)
      .sortBy(b => b.dateCreated)
      .reverse()
      .value();

    var time_style = {
      float: 'right',
      marginRight: 10,
      color: '#333'
    };

    var on_click = build_id => {
      return evt => {
        this.props.pageElem.setState({
          activeBuildID: build_id
        });
      };
    };

    var entries = _.map(builds, b => {
      var build_state = get_build_state(b);

      var classes = "buildsSideItem";
      if (this.props.activeBuildID === b.id) {
        classes += " lt-lightgray-bg";
      }

      var failed = null;
      if (build_state === 'failed' || build_state === 'nothing') {
        if (b.stats.test_failures === 0) {
          failed = <div className="lt-red" style={{marginTop: 3}}>
            Failed
          </div>;
        } else {
          var text = b.stats.test_failures === 1 ? 'test failed' : 
            'tests failed';

          failed = <div className="lt-red" style={{marginTop: 3}}>
            {b.stats.test_failures}{" "}{text}
          </div>;
        }
      }

      return <div className={classes} onClick={on_click(b.id)}>
        <div style={{display: 'inline-block'}}>{b.project.name}</div>
        <div style={time_style}>{display_duration(b.duration / 1000)}</div>
        <div className="subText">
          Triggered by {get_build_cause(b)}
          {", "}
          {b.stats.test_count}
          {b.stats.test_count === 1 ? " test run" : " tests run"}
        </div>
        {failed}
      </div>
    });

    return <div>
      {entries}
    </div>;
  },

  renderSurroundingBuilds: function() {
    // TODO
    return null;

    if (this.props.type === "diff") {
      return null;
    }
    return this.renderSection("Nearby Commits", <span>TODO</span>);
  },

  renderOtherActions: function() {
    return this.renderSection(
      'Other Actions',
      <a className="buildsSideItem">
        Create New Build [TODO]
      </a>
    );
  },

  renderSection: function(header, content) {
    return <div className="marginTopL">
      <div className="buildsSideSectionHeader">{header}</div>
      <div>{content}</div>
    </div>;
  }
});

export default Sidebar;
