import React, { PropTypes } from 'react';
import moment from 'moment';

import ChangesLinks from 'es6!display/changes/links';
import { TimeText, display_duration } from 'es6!display/time';
import { buildSummaryText, manyBuildsSummaryText, get_build_cause } from 'es6!display/changes/build_text';
import { get_builds_for_last_change } from 'es6!display/changes/builds';
import { get_runnable_condition, get_runnables_summary_condition, ConditionDot } from 'es6!display/changes/build_conditions';

import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

/*
 * The sidebar on the builds page. Shows a list of builds for a single diff or
 * commit
 */

var Sidebar = React.createClass({

  propTypes: {
    // list of builds to render in side bar
    builds: PropTypes.array,

    // are we rendering for a diff or a commit
    type: PropTypes.oneOf(['diff', 'commit']),

    // if its a diff, grab its information
    targetData: PropTypes.object,

    // which build are we currently showing, if any
    activeBuildID: PropTypes.string,

    // the parent page element. Sidebar clicks change its state
    pageElem: PropTypes.element,
  },

  render: function() {
    return <div className="buildsSidebar">
      {this.renderBuildsList()}
      {this.renderSection('Links', this.renderLinksToCode())}
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

    var label = <span>
      Committed {"("}<TimeText time={source.revision.dateCommitted} />{")"}
    </span>;

    var content = this.noBuildsMarkup();
    if (builds) {
      content = this.renderBuilds();
    }

    return <div>
      <div className="marginTopL">
        {this.renderLatestItem(builds)}
      </div>
      {this.renderSection(label, content)}
    </div>;
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

    var sections = [], latest_item = null;
    _.each(all_diff_ids, (single_diff_id, index) => {
      var diff_builds = builds_by_update[single_diff_id];
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
      var section_content = this.noBuildsMarkup();
      if (diff_builds) {
        section_content = this.renderBuilds(diff_builds);
      }

      sections.push(this.renderSection(section_header, section_content));
    });

    return <div>
      <div className="marginTopL">
        {this.renderLatestItem(builds)}
      </div>
      {sections}
    </div>;
  },

  noBuildsMarkup: function() {
    return <div className="buildsSidebarNoBuilds">
      <i className="fa fa-exclamation-circle" />
      <span className="marginLeftS">No builds</span>
    </div>;
  },

  renderLatestItem: function(builds) {
    // if its a diff, only get builds from the most recent update that had 
    // builds
    builds = get_builds_for_last_change(builds);

    // we want the most recent build for each project
    var latestByProj = _.chain(builds)
      .groupBy(b => b.project.name)
      .map(projBuilds => _.last(_.sortBy(projBuilds, b => b.dateCreated)))
      .values()
      .value();

    var subtext = manyBuildsSummaryText(latestByProj);

    var summaryCondition = get_runnables_summary_condition(latestByProj);
    var subtextExtraClass = summaryCondition.indexOf('failed') === 0 ?
      'redGrayMix' : '';

    return this.renderBuildSideItem(
      <ConditionDot
        condition={summaryCondition}
        size="medium"
        glow={latestByProj.length > 1}
      />,
      'Latest Builds',
      '',
      subtext,
      subtextExtraClass,
      null,
      !this.props.activeBuildID,
      evt => this.props.pageElem.setState({ activeBuildID: null })
    );
  },

  renderBuilds: function(builds) {
    if (builds === undefined) {
      return null;
    }
    builds = _.chain(builds)
      .sortBy(b => b.dateCreated)
      .reverse()
      .value();

    var on_click = build_id => {
      return evt => {
        this.props.pageElem.setState({
          activeBuildID: build_id
        });
      };
    };

    var entries = _.map(builds, b => {
      var buildCondition = get_runnable_condition(b);
      var subtextExtraClass = buildCondition.indexOf('failed') === 0 ?
        'redGrayMix' : null;

      return this.renderBuildSideItem(
        <ConditionDot
          condition={buildCondition}
          size="medium"
        />,
        utils.truncate(b.project.name, 26),
        display_duration(b.duration / 1000),
        `${buildSummaryText(b)}`,
        subtextExtraClass,
        get_build_cause(b),
        this.props.activeBuildID === b.id,
        on_click(b.id));
    });

    return <div>{entries}</div>;
  },

  renderBuildSideItem: function(condition_dot, text, time, subtext,
    subtext_extra_class, right_subtext, is_selected, on_click) {

    var time_style = {
      float: 'right',
      marginRight: 10,
      color: '#333'
    };

    var classes = cx({
      buildsSideItem: true,
      selected: is_selected
    });

    if (right_subtext) {
      var className = 'floatR marginRightM subText';
      right_subtext = <div className={className}>
        {right_subtext}
      </div>;
    }

    return <div className={classes} onClick={on_click}>
      <div className="sideItemDot">
        {condition_dot}
      </div>
      <div>
        <div className="inlineBlock">{text}</div>
        <div style={time_style}>{time}</div>
        <div className={"subText " + subtext_extra_class}>
          {subtext}
          {right_subtext}
        </div>
      </div>
    </div>;
  },

  renderLinksToCode() {
    if (this.props.type === "diff") {
      var diffData = this.props.targetData;
      return <div className="marginBottomL"> <a
        className="external"
        href={diffData.uri}
        target="_blank">
        <i className="fa fa-pencil marginRightS" style={{width: 15}} />
        View Differential Revision
      </a> </div>;
    } else {
      var source = this.props.targetData;

      var diffHref = null;
      URI.withinString(source.revision.message, (url) => {
        if (URI(url).path().match(/D[0-9]+/)) {
          // its a phabricator diff
          diffHref = url;
        }
        return url;
      });

      var commitLink = <div> <a 
        className="external"
        href={ChangesLinks.phabCommitHref(source.revision)}
        target="_blank">
        <i className="fa fa-code marginRightS" style={{width: 15}} />
        View Commit
      </a> </div>;

      var diffLink = null;
      if (diffHref) {
        diffLink = <div className="marginTopS"> <a
          className="external"
          href={diffHref}
          target="_blank">
          <i className="fa fa-pencil marginRightS" style={{width: 15}} />
          View Original Differential Revision
        </a> </div>;
      }

      return <div>
        {commitLink}
        {diffLink}
      </div>
    }
  },

  renderSection: function(header, content) {
    return <div className="marginTopL">
      <div className="buildsSideSectionHeader">{header}</div>
      <div>{content}</div>
    </div>;
  }
});

export default Sidebar;
