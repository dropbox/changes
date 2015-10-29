import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import SectionHeader from 'es6!display/section_header';
import { AjaxError } from 'es6!display/errors';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import ChangesLinks from 'es6!display/changes/links';
import { Grid, GridRow } from 'es6!display/grid';
import { Tabs, MenuUtils } from 'es6!display/menus';
import { TestDetails } from 'es6!display/changes/test_details';
import { TimeText } from 'es6!display/time';

import InteractiveData from 'es6!pages/helpers/interactive_data';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

let AdminPage = React.createClass({

  menuItems: [
    'Projects',
  ],

  getInitialState: function() {
    return {
      selectedItem: null, // set in componentWillMount
    }
  },

  componentWillMount: function() {
    let selectedItemFromHash = MenuUtils.selectItemFromHash(
      window.location.hash, this.menuItems);

    // when we first came to this page, which tab was shown? Used by the
    // initial data fetching within tabs
    this.initialTab = selectedItemFromHash || 'Projects';

    this.setState({ selectedItem: this.initialTab });
  },

  componentDidMount: function() {
    api.fetch(this, {
      projects: '/api/0/projects/',
    });
  },

  render: function() {
    if (!api.isLoaded(this.state.projects)) {
      return <APINotLoadedPage calls={this.state.projects} />;
    }
    let projects = this.state.projects.getReturnedData();

    let title = 'Admin Panel'
    utils.setPageTitle(title);

    // render menu
    let selectedItem = this.state.selectedItem;

    let menu = <Tabs
      items={this.menuItems}
      selectedItem={selectedItem}
      onClick={MenuUtils.onClick(this, selectedItem)}
    />;

    let content = null;
    switch (selectedItem) {
      case 'Projects':
        content = this.renderProjects();
        break;
      default:
        throw 'unreachable';
    }

    return <ChangesPage highlight="Projects">
      <SectionHeader>{title}</SectionHeader>
      {menu}
      <div className="marginTopS">{content}</div>
    </ChangesPage>;
  },

  renderProjects: function() {
    if (!api.isLoaded(this.state.projects)) {
      return <APINotLoadedPage calls={this.state.projects} />;
    }
    let projects = this.state.projects.getReturnedData();

    let rows = [];
    _.each(projects, project => {
      rows.push([
        ChangesLinks.projectAdmin(project),
        project.status.name,
        <TimeText time={project.dateCreated} />
      ]);
    });

    return <div>
      <Grid
        colnum={3}
        className="marginBottomM marginTopM"
        data={rows}
        headers={['Name', 'Status', 'Creation Date']}
      />
    </div>;
  },
});