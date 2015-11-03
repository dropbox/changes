import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import SectionHeader from 'es6!display/section_header';
import { AjaxError } from 'es6!display/errors';
import { Button } from 'es6!display/button';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import ChangesLinks from 'es6!display/changes/links';
import { Grid, GridRow } from 'es6!display/grid';
import Request from 'es6!display/request';
import { Tabs, MenuUtils } from 'es6!display/menus';
import { TestDetails } from 'es6!display/changes/test_details';
import { TimeText } from 'es6!display/time';

import InteractiveData from 'es6!pages/helpers/interactive_data';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

let AdminProjectPage = React.createClass({

  menuItems: [
    'Settings',
    'Snapshots',
    'Build Plans',
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
      snapshots: `/api/0/projects/${slug}/snapshots`,
      plans: `/api/0/projects/${slug}/plans/?status=`,
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
        content = <ProjectSettingsFieldGroup project={project} />
        break;
      case 'Snapshots':
        if (!api.isLoaded(this.state.snapshots)) {
          return <APINotLoadedPage calls={this.state.snapshots} />;
        }
        let snapshots = this.state.snapshots.getReturnedData();
        content = <SnapshotList snapshots={snapshots} projectSlug={project.slug} />
        break;
     case 'Build Plans':
        if (!api.isLoaded(this.state.plans)) {
          return <APINotLoadedPage calls={this.state.plans} />;
        }
        let plans = this.state.plans.getReturnedData();
        content = <PlanList plans={plans} projectSlug={project.slug} />
        break;
      default:
        throw 'unreachable';
    }

    return <ChangesPage highlight="Project Settings">
      <SectionHeader>{title}</SectionHeader>
      {menu}
      <div className="marginTopS">{content}</div>
    </ChangesPage>;
  },
});

let createFieldGroupMarkup = function(form, saveButtonText, _this) {
  let markup = _.map(form, section => {

    let sectionMarkup = _.map(section.fields, field => {

      if (field.type === 'text' || field.type === 'textarea' || field.type === 'select') {
        let placeholder = field.placeholder || '';

        let commentMarkup = null;
        if (field.comment) {
          commentMarkup = <div> {field.comment} </div>;
        }

        let tag = '';
        if (field.type === 'text') {
          tag = <input size="50" type="text" valueLink={_this.linkState(field.link)} placeholder={placeholder}/>;
        } else if (field.type === 'textarea') {
          tag = <textarea rows="10" cols="100" valueLink={_this.linkState(field.link)} placeholder={placeholder}/>;
        } else if (field.type === 'select') {
          let options = _.map(field.options, option => <option value={option}>{option}</option>);
          tag = <select valueLink={_this.linkState(field.link)} >{options}</select>;
        }

        return <div className="marginBottomS">
          <div> {field.display}: </div>
          {tag}
          {commentMarkup}
          <hr />
        </div>;
      } else if (field.type === 'checkbox') {
        return <div className="marginBottomS">
          <label>
            <div><input type='checkbox' checkedLink={_this.linkState(field.link)} /></div>
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

  let onSaveClicked = _ => _this.saveSettings();
  let saveButton = <Button onClick={onSaveClicked}>{saveButtonText}</Button>;
  return <div>{saveButton}{markup}</div>;
}

let ProjectSettingsFieldGroup = React.createClass({

  mixins: [React.addons.LinkedStateMixin],

  propTypes: {
    project: PropTypes.object.isRequired,
  },

  getInitialState: function() {
    return { };
  },

  displayStatusToStatus: {
    'Active': 'active',
    'Inactive': 'inactive',
  },

  saveSettings: function() {
    let state = this.state;
    let project_params = {
      'name': state.name,
      'repository': state.repository,
      'slug': state.slug,
      'status': this.displayStatusToStatus[state.status],
    };
    let options_params = {
      'project.owners': state.owner,
      'project.notes': state.notes,
      'build.commit-trigger': state.commitTrigger | 0,
      'phabricator.diff-trigger': state.diffTrigger | 0,
      'build.file-whitelist': state.fileWhitelist,
      'build.branch-names': state.branches,
      'mail.notify-author': state.notifyAuthors | 0,
      'mail.notify-addresses': state.notifyAddresses,
      'mail.notify-addresses-revisions': state.notifyAddressesRevision,
      'phabricator.notify': state.pushBuildResults | 0,
      'phabricator.coverage': state.pushCoverageResults | 0,
      'green-build.notify': state.greenBuildNotify | 0,
      'green-build.project': state.greenBuildProject,
      'ui.show-tests': state.showTests | 0,
      'build.test-duration-warning': state.maxTestDuration,
      'ui.show-coverage': state.showCoverage | 0,
    };

    let originalSlug = this.props.project.slug;

    let endpoints = {
      '_postRequest_project': `/api/0/projects/${originalSlug}/`,
      '_postRequest_options': `/api/0/projects/${originalSlug}/options/`,
    };
    let params = {
      '_postRequest_project': project_params,
      '_postRequest_options': options_params,
    };

    api.post(this, endpoints, params);
  },

  componentDidMount: function() {
    let project = this.props.project;
    this.setState({ name: project.name,
                    slug: project.slug,
                    repository: project.repository.url,
                    status: project.status.id,
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
        {type: 'select', options: ['Active', 'Inactive'], display: 'Status', link: 'status'},
        {type: 'text', display: 'Owner', link: 'owner', comment: 'An email address for whom should be contacted in case of questions about this project.'},
        {type: 'textarea', display: 'Notes', link: 'notes', comment: 'A blurb of text to give additional context around this project. This will be shown in various places, such as in email notifications.'},
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

    return createFieldGroupMarkup(form, "Save Project", this);
  },
});

let SnapshotList = React.createClass({

  propTypes: {
    projectSlug: PropTypes.string.isRequired,
    snapshots: PropTypes.array.isRequired,
  },

  getInitialState: function() {
    return { };
  },

  render: function() {
    let rows = _.map(this.props.snapshots, snapshot => {
      let sha = '-';
      if (snapshot.source.revision.sha) {
        sha = snapshot.source.revision.sha.substring(0, 12);
      }

      let params = {};
      let key = 'snapshot.current';
      let action = 'Activate';
      if (snapshot.isActive) {
        params[key] = '';
        action = 'Deactivate';
      } else {
        params[key] = snapshot.id;
      }
      let endpoint = `/api/0/projects/${this.props.projectSlug}/options/`;
      let post = <Request
                    parentElem={this}
                    name="activate_snapshot"
                    endpoint={endpoint}
                    method="post"
                    params={params}>
                      <Button type="blue">
                        <span>{action}</span>
                      </Button>
                 </Request>;
      return [snapshot.id, sha, <TimeText time={snapshot.dateCreated} />, post];
    });

    return <Grid
             colnum={4}
             cellClasses={['wide', 'nowrap', 'nowrap', 'nowrap']}
             data = {rows}
             headers={['Id', 'Sha', 'Created', 'Status']}
           />;
  },
});

let PlanList = React.createClass({

  propTypes: {
    projectSlug: PropTypes.string.isRequired,
    plans: PropTypes.array.isRequired,
  },

  getInitialState: function() {
    return {
      expandedPlans: {},
    };
  },

  render: function() {
    let rows = [];
    _.each(this.props.plans, plan => {
      let onClick = __ => {
        this.setState(
          utils.update_key_in_state_dict('expandedPlans',
            plan.id,
            !this.state.expandedPlans[plan.id])
        );
      };

      var expandLabel = !this.state.expandedPlans[plan.id] ?
        'Expand Plan' : 'Collapse Plan';

      var planName = <div>
        {plan.name} <a onClick={onClick}>{expandLabel}</a>
      </div>;

      rows.push([planName, plan.status.name, <TimeText time={plan.dateCreated} />]);

      if (this.state.expandedPlans[plan.id]) {
        rows.push(GridRow.oneItem(
          <PlanDetailsWrapper plan={plan} />
        ));
      }
    });

    return <Grid
             colnum={3}
             cellClasses={['wide', 'nowrap', 'nowrap']}
             data = {rows}
             headers={['Plan', 'Status', 'Created']}
           />;
  },
});

// Use this wrapper to fetch the plan options and then render the plan details.
let PlanDetailsWrapper = React.createClass({

  propTypes: {
    plan: PropTypes.object.isRequired,
  },

  getInitialState: function() {
    return { };
  },

  componentDidMount: function() {
    api.fetch(this, {
      options: `/api/0/plans/${this.props.plan.id}/options`,
    });
  },

  render: function() {
    if (!api.isLoaded(this.state.options)) {
      return <APINotLoadedPage calls={this.state.options} />;
    }
    let options = this.state.options.getReturnedData();

    return <PlanDetails options={options} plan={this.props.plan} />;
  },
});

let PlanDetails = React.createClass({

  mixins: [React.addons.LinkedStateMixin],

  propTypes: {
    plan: PropTypes.object.isRequired,
    options: PropTypes.object.isRequired,
  },

  getInitialState: function() {
    return {
      expandedSteps: {},
    };
  },

  saveSettings: function() {
    let state = this.state;
    let plan_params = {
      'name': state.name,
      'status': state.status,
    };
    let options_params = {
      'build.expect-tests': state.expectTests | 0,
      'snapshot.allow': state.allowSnapshot | 0,
    };

    let planId = this.props.plan.id;

    let endpoints = {
      '_postRequest_plan': `/api/0/plans/${planId}/`,
      '_postRequest_options': `/api/0/plans/${planId}/options/`,
    };
    let params = {
      '_postRequest_plan': plan_params,
      '_postRequest_options': options_params,
    };

    api.post(this, endpoints, params);
  },

  componentDidMount: function() {
    let project = this.props.project;
    this.setState({ name: this.props.plan.name,
                    status: this.props.plan.status.name,
                    expectTests: this.props.options['build.expect-tests'] === '1',
                    allowSnapshot: this.props.options['snapshot.allow'] === '1',
                  });
  },

  render: function() {
    let form = [
      { sectionTitle: 'Basics', fields: [
        {type: 'text', display: 'Name', link: 'name'},
        {type: 'text', display: 'Status', link: 'status'},
        ]
      },
      { sectionTitle: 'Snapshots', fields: [
        {type: 'checkbox', link: 'allowSnapshot', comment: 'Allow snapshots to be created (and used) for this build plan.'},
        ]
      },
      { sectionTitle: 'Tests', fields: [
        {type: 'checkbox', link: 'expectTests',
         comment: 'Expect test results to be reported. If they\'re not, the build will be considered as failing, in addition to "failing during setup".'},
        ]
      },
    ];

    let fieldMarkup = createFieldGroupMarkup(form, "Save Plan", this);
    let rows = [];
    _.each(this.props.plan.steps, step => {
      let onClick = __ => {
        this.setState(
          utils.update_key_in_state_dict('expandedSteps',
            step.id,
            !this.state.expandedSteps[step.id])
        );
      };

      var expandLabel = !this.state.expandedSteps[step.id] ?
        'Expand Step' : 'Collapse Step';

      var stepName = <div>
        {step.name} <a onClick={onClick}>{expandLabel}</a>
      </div>;

      rows.push([step.order,
                 stepName,
                 <Request
                   parentElem={this}
                   name="deleteStep"
                   method="delete"
                   endpoint={`/api/0/steps/${step.id}/`}>
                     <Button>Delete</Button>
                  </Request>,
                 <TimeText time={step.dateCreated} />]);

      if (this.state.expandedSteps[step.id]) {
        rows.push(GridRow.oneItem(
          <StepDetails step={step} />
        ));
      }
    });

    return <div>
             {fieldMarkup}
             <Grid
               colnum={4}
               cellClasses={['nowrap', 'wide', 'nowrap', 'nowrap']}
               data = {rows}
               headers={['Order', 'Step', 'Delete', 'Created']}
             />
           </div>;
  },
});

let StepDetails = React.createClass({

  mixins: [React.addons.LinkedStateMixin],

  propTypes: {
    step: PropTypes.object.isRequired,
  },

  getInitialState: function() {
    return {};
  },

  changesBuildStepImplementationFor: {
    'DefaultBuildStep': 'changes.buildsteps.default.DefaultBuildStep',
    'LXCBuildStep': 'changes.buildsteps.lxc.LXCBuildStep',
    'JenkinsBuildStep': 'changes.backends.jenkins.buildstep.JenkinsBuildStep',
    'JenkinsGenericBuildStep': 'changes.backends.jenkins.buildstep.JenkinsGenericBuildStep',
    'JenkinsCollectorBuildStep': 'changes.backends.jenkins.buildsteps.collector.JenkinsCollectorBuildStep',
    'JenkinsTestCollectorBuildStep': 'changes.backends.jenkins.buildsteps.test_collector.JenkinsTestCollectorBuildStep',
  },

  saveSettings: function() {
    let state = this.state;
    let step_params = {
      'name': state.name,
      'build.timeout': state.timeout,
      'data': state.data,
      'implementation': this.changesBuildStepImplementationFor[state.implementation],
    };

    let stepId = this.props.step.id;

    let endpoints = {
      '_postRequest_step': `/api/0/steps/${stepId}/`,
    };
    let params = {
      '_postRequest_step': step_params,
    };

    api.post(this, endpoints, params);
  },

  componentDidMount: function() {
    let step = this.props.step;
    var implementation = step.implementation.split('.');
    this.setState({ name: step.name,
                    timeout: step.options['build.timeout'],
                    data: step.data,
                    implementation: implementation[implementation.length - 1],
                  });
  },

  render: function() {
    let form = [
      { sectionTitle: '', fields: [
        {type: 'select', display: 'Implementation', link: 'implementation',
         options: Object.keys(this.changesBuildStepImplementationFor) },
        {type: 'textarea', display: 'Config', link: 'data'},
        {type: 'text', display: 'Timeout', link: 'timeout'},
        ]
      },
    ];

    return createFieldGroupMarkup(form, "Save Step", this);
  },
});

export default AdminProjectPage;
