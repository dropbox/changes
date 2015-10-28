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
    'Settings',
    //'Snapshots',
    //'Build Plans'
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
    let slug = this.props.projectSlug;
    api.fetch(this, {
      project: `/api/0/projects/${slug}`,
    });
  },

  render: function() {
    if (!api.isLoaded(this.state.project)) {
      return <APINotLoadedPage calls={this.state.project} />;
    }
    let project = this.state.project.getReturnedData();

    let title = 'Project Settings'
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
        content = <FieldGroup project={project} />
        break;
      default:
        throw 'unreachable';
    }

    return <ChangesPage highlight="Project Settings">
      <SectionHeader>{title}</SectionHeader>
      <h4> These are readonly for now, use changes-classic to modify settings </h4>
      {menu}
      <div className="marginTopS">{content}</div>
    </ChangesPage>;
  },
});

let FieldGroup = React.createClass({

  mixins: [React.addons.LinkedStateMixin],

  getInitialState: function() {
    return { };
  },

  componentDidMount: function() {
    let project = this.props.project;
    this.setState({ name: project.name,
                    slug: project.slug,
                    repository: project.repository.url,
                    status: project.status.name,
                    owner: project.options['project.owners'],
                    notes: project.options['project.notes'],
                    commitTrigger: project.options['build.commit-trigger'] === '1',
                    diffTrigger: project.options['phabricator.diff-trigger'] === '1',
                    fileWhitelist: project.options['build.file-whitelist'],
                    branches: project.options['build.branch-names'],
                    notifyAuthors: project.options['mail.notify-author'] === '1',
                    notifyAddresses: project.options['mail.notify-addresses'],
                    notifyAddressesRevisions: project.options['mail.notify-addresses-revisions'],
                    pushBuildResults: project.options['phabricator.notify'] === '1',
                    pushCoverageResults: project.options['phabricator.coverage'] === '1',
                    greenBuildNotify: project.options['green-build.notify'] === '1',
                    greenBuildProject: project.options['green-build.project'],
                    showTests: project.options['ui.show-tests'] === '1',
                    maxTestDuration: project.options['build.test-duration-warning'],
                    showCoverage: project.options['ui.show-coverage'] === '1',
                  });
  },

  render: function() {
    let form = [
      { sectionTitle: 'Basics', fields: [
        {type: 'text', display: 'Name', link: 'name'},
        {type: 'text', display: 'Slug', link: 'slug'},
        {type: 'text', display: 'Repository', link: 'repository'},
        {type: 'text', display: 'Status', link: 'status'},
        {type: 'text', display: 'Owner', link: 'owner', comment: 'An email address for whom should be contacted in case of questions about this project.'},
        {type: 'text', display: 'Notes', link: 'notes', comment: 'A blurb of text to give additional context around this project. This will be shown in various places, such as in email notifications.'},
        ]
      },
      { sectionTitle: 'Builds', fields: [
        {type: 'checkbox', link: 'commitTrigger', comment: 'Automatically create builds for new commits.'},
        {type: 'checkbox', link: 'diffTrigger', comment: 'Automatically create builds for Phabricator diffs.'},
        {type: 'textarea', display: 'File Whitelist', link: 'fileWhitelist',
         comment: "Only trigger builds when a file matches one of these patterns. Separate patterns with newlines. Use '*' for wildcards.",
         placeholder: 'i.e. src/project/*'},
        {type: 'text', display: 'Branches', link: 'branches',
         comment: "Limit commit triggered builds to these branches. Separate branch names with spaces. Use '*' for wildcards."},
        ]
      },
      { sectionTitle: 'Mail', fields: [
        {type: 'checkbox', link: 'notifyAuthors', comment: 'Notify authors of build failures.'},
        {type: 'text', display: 'Addresses to notify of any build failure', link: 'notifyAddresses'},
        {type: 'text', display: 'Addresses to notify of failures from commits (not patches)', link: 'notifyAddressesRevisions'},
        ]
      },
      { sectionTitle: 'Phabricator', fields: [
        {type: 'checkbox', link: 'pushBuildResults', comment: 'Push build results to Phabricator (diffs).'},
        {type: 'checkbox', link: 'pushCoverageResults', comment: 'Push coverage results to Phabricator (diffs).'},
        ]
      },
      { sectionTitle: 'Green Build', fields: [
        {type: 'checkbox', link: 'greenBuildNotify', comment: 'Notify of passing builds.'},
        {type: 'text', display: 'Project Name', link: 'greenBuildProject', placeholder: 'e.g. ' + this.props.project.slug},
        ]
      },
      { sectionTitle: 'Tests', fields: [
        {type: 'checkbox', link: 'showTests', comment: 'Show test data in various UIs.'},
        {type: 'text', display: 'Maximum Duration (per test)', link: 'maxTestDuration',
         comment: 'Tests exceeding this duration (in ms) will show up as warnings.'},
        ]
      },
      { sectionTitle: 'Code Coverage', fields: [
        {type: 'checkbox', link: 'showCoverage', comment: 'Show coverage data in various UIs.'},
        ]
      },
      ];

    let markup = _.map(form, section => {

      let sectionMarkup = _.map(section.fields, field => {

        if (field.type === 'text' || field.type === 'textarea') {
          let placeholder = field.placeholder || '';

          let commentMarkup = null;
          if (field.comment) {
            commentMarkup = <div> {field.comment} </div>;
          }

          return <div className="marginBottomS">
            <div> {field.display}: </div>
            <div> <input type={field.type} valueLink={this.linkState(field.link)} placeholder={placeholder}/> </div>
            {commentMarkup}
            <hr />
          </div>;
        } else if (field.type === 'checkbox') {
          return <div className="marginBottomS">
            <label>
              <input type='checkbox' checkedLink={this.linkState(field.link)} />
              {field.comment}
            </label>
            <hr />
          </div>;
        } else {
          throw 'unreachable';
        }
      });

      return <div>
        <h2>{section.sectionTitle}</h2>
        {sectionMarkup}
      </div>;
    });

    return <div>{markup}</div>;
  },
});

export default AdminPage;
