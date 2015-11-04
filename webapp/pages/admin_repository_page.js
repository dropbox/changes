import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import SectionHeader from 'es6!display/section_header';
import { Button } from 'es6!display/button';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import ChangesLinks from 'es6!display/changes/links';
import * as FieldGroupMarkup from 'es6!display/field_group';
import { Grid, GridRow } from 'es6!display/grid';
import Request from 'es6!display/request';
import { Tabs, MenuUtils } from 'es6!display/menus';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

let AdminRepositoryPage = React.createClass({

  menuItems: [
    'Settings',
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
    this.initialTab = selectedItemFromHash || 'Settings';
    this.setState({ selectedItem: this.initialTab });
  },

  componentDidMount: function() {
    let repositoryID = this.props.repositoryID;
    api.fetch(this, {
      repository: `/api/0/repositories/${repositoryID}`,
      projects: `/api/0/repositories/${repositoryID}/projects`,
    });
  },

  render: function() {
    if (!api.isLoaded(this.state.repository)) {
      return <APINotLoadedPage calls={this.state.repository} />;
    }
    let repository = this.state.repository.getReturnedData();

    let title = repository.url;
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
      case 'Settings':
        content = <RepositorySettingsFieldGroup repository={repository} />
        break;
      case 'Projects':
        if (!api.isLoaded(this.state.projects)) {
          return <APINotLoadedPage calls={this.state.projects} />;
        }
        content = <ProjectList projects={this.state.projects.getReturnedData()} />
        break;
      default:
        throw 'unreachable';
    }

    return <ChangesPage highlight="Repository Settings">
      <SectionHeader>{title}</SectionHeader>
      {menu}
      <div className="marginTopS">{content}</div>
    </ChangesPage>;
  },
});

let RepositorySettingsFieldGroup = React.createClass({

  mixins: [React.addons.LinkedStateMixin],

  propTypes: {
    repository: PropTypes.object.isRequired,
  },

  getInitialState: function() {
    return { };
  },

  saveSettings: function() {
    let state = this.state;
    let params = {
      'url': state.url,
      'backend': state.backend,
      'status': state.status,
      'auth.username': state.username,
      'auth.private-key-file': state.privateKeyFile,
      'phabricator.callsign': state.callsign,
    };

    let endpoints = {
      '_postRequest_repository': `/api/0/repositories/${this.props.repository.id}/`,
    };
    params = {
      '_postRequest_repository': params,
    };

    api.post(this, endpoints, params);
  },

  componentDidMount: function() {
    let repository = this.props.repository;
    this.setState({ url: repository.url,
                    status: repository.status.id,
                    backend: repository.backend.id,
                    username: repository.options['auth.username'],
                    privateKeyFile: repository.options['auth.private-key-file'],
                    callsign: repository.options['phabricator.callsign'],
                  });
  },

  render: function() {
    let form = [
      { sectionTitle: 'Basics', fields: [
        {type: 'text', display: 'URL', link: 'url'},
        {type: 'select', options: {'Active': 'active', 'Inactive': 'inactive'}, display: 'Status', link: 'status'},
        {type: 'select', options: {'Unknown': 'unknown', 'Git': 'git', 'Mercurial': 'hg'}, display: 'Backend', link: 'backend'},
        ]
      },
      { sectionTitle: 'Credentials', fields: [
        {type: 'text', display: 'Username', link: 'username', placeholder: 'Defaults to vcs backend.'},
        {type: 'text', display: 'Private Key File', link: 'privateKeyFile', placeholder: 'i.e. ~/.ssh/id_rsa.'},
        ]
      },
      { sectionTitle: 'Phabricator', fields: [
        {type: 'text', display: 'Callsign', link: 'callsign'},
        ]
      },
    ];

    return FieldGroupMarkup.create(form, "Save Repository", this);
  },
});


let ProjectList = React.createClass({

  propTypes: {
    projects: PropTypes.array.isRequired,
  },

  getInitialState: function() {
    return { };
  },

  render: function() {
    let rows = _.map(this.props.projects, project => {
      return [ChangesLinks.projectAdmin(project)];
    });

    return <Grid
             colnum={1}
             data = {rows}
             headers={['Projects']}
           />;
  },
});

export default AdminRepositoryPage
