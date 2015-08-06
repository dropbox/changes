import React from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesPage from 'es6!display/page_chrome';
import { Menu2, MenuUtils } from 'es6!display/menus';
import { ProgrammingError } from 'es6!display/errors';

import BuildsTab from 'es6!pages/project/builds_tab';
import CommitsTab from 'es6!pages/project/commits_tab';
import DataControls from 'es6!pages/helpers/data_controls';
import DetailsTab from 'es6!pages/project/details_tab';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';
import colors from 'es6!utils/colors';

var cx = React.addons.classSet;

var ProjectPage = React.createClass({

  getInitialState: function() {
    return {
      selectedItem: 'Commits', // duplicated in componentDidMount
      project: null,
      commits: null,
      details: null,

      // Keep the state for the commit tab here (and send it via props.) This
      // preserves the state if the user clicks to another tab
      commitsState: {},

      // same, but for builds state
      buildsControls: {}
    }
  },

  menuItems: [
    'Commits',
    'Builds',
    'Tests [TODO]',
    'Project Details'
  ],

  componentWillMount: function() {
    // show the right menu tab if our url contains a hash
    var selected_item_from_hash = MenuUtils.selectItemFromHash(
      window.location.hash, this.menuItems);

    if (selected_item_from_hash) {
      this.setState({ selectedItem: selected_item_from_hash });
    }

    // initialize our pagination object(s). Data fetching still doesn't happen
    // till componentDidMount.
    this.setState({
      buildsControls: DataControls(
        this,
        'buildsControls',
        BuildsTab.getEndpoint(this.props.projectSlug))
    });
  },

  componentDidMount: function() {
    var slug = this.props.projectSlug;

    // we grab most everything in parallel now. Its easy enough to later
    // switch this to trigger on menu click (which the builds tab does now)
    api.fetch(this, {
      project: `/api/0/projects/${slug}`,
      commits: CommitsTab.getAPIEndpoint(slug),
      details: DetailsTab.getAPIEndpoint(slug)
    });
  },

  render: function() {
    if (!api.isLoaded(this.state.project)) {
      return <APINotLoaded state={this.state.projects} isInline={false} />;
    }

    // render menu
    var selected_item = this.state.selectedItem;
    var onClick = item => {
      if (item === selected_item) {
        return;
      }

      window.history.replaceState(
        null,
        'changed tab',
        URI(window.location.href)
          .search("")
          .hash(item.replace(/ /g, ""))
          .toString()
      );
      this.setState({selectedItem: item});
    }
    var menu = <Menu2
      items={this.menuItems}
      selectedItem={selected_item}
      onClick={onClick}
    />;

    var content = null;
    switch (selected_item) {
      case 'Commits':
        content = <CommitsTab
          project={this.state.project}
          data={this.state.commits}
          myState={this.state.commitsState}
          pageElem={this}
        />;
        break;
      case 'Builds':
        content = <BuildsTab
          project={this.state.project}
          controls={this.state.buildsControls}
          pageElem={this}
        />;
        break;
      case 'Tests [TODO]':
        content = <div>TODO</div>;
        break;
      case 'Project Details':
        content = <DetailsTab
          project={this.state.project}
          data={this.state.details}
        />;
        break;
      default:
        content = <ProgrammingError>
          Unknown tab {selected_item}
        </ProgrammingError>;
    }

    var padding_classes = 'paddingLeftM paddingRightM';
    return <ChangesPage bodyPadding={false}>
      {this.renderProjectInfo(this.state.project.getReturnedData())}
      <div className={padding_classes}>
        {menu}
        {content}
      </div>
    </ChangesPage>;
  },

  renderProjectInfo: function(project_info) {
    var style = {
      padding: 10,
      backgroundColor: colors.lightestGray
    };

    var triggers = _.compact([
      project_info.options["phabricator.diff-trigger"] ? "Diffs" : null,
      project_info.options["build.commit-trigger"] ? "Commits" : null,
    ]);

    var branches_option = project_info.options["build.branch-names"] || '*';
    if (branches_option === "*") {
      var branches = "all branches";
    } else if (branches_option.split(" ").length === 1) {
      var branches = `only on ${branches_option} branch`;
    } else {
      var branches = "branches: " + branches_option.replace(/ /g, ", ");
    }

    var whitelist_msg = "";
    var whitelist_option = project_info.options["build.file-whitelist"];
    if (whitelist_option) {
      var whitelist_paths = utils.split_lines(whitelist_option);
      whitelist_msg = <b>
        Builds are only run for changes that touch
        {" "}
        <span style={{borderBottom: "2px dotted #ccc"}}>
          certain paths
        </span>
        {"."}
      </b>
    }

    return <div style={style}>
      <div><span style={{fontWeight: 900}}>{project_info.name}</span></div>
      <b>Repository:</b>
        {" "}{project_info.repository.url}{" "}
        {" ("}
        {branches}
        {")"}
      <div>{whitelist_msg}</div>
    </div>;
  }
});

export default ProjectPage;
