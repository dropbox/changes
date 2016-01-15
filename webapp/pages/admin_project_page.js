import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import SectionHeader from 'es6!display/section_header';
import { AjaxError } from 'es6!display/errors';
import { Button } from 'es6!display/button';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import ChangesLinks from 'es6!display/changes/links';
import * as FieldGroupMarkup from 'es6!display/field_group';
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
    'New Build Plan',
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
      case 'New Build Plan':
        content = <NewPlan project={project} />;
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
      'status': state.status,
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
      'mail.notify-addresses-revisions': state.notifyAddressesRevisions,
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
        {type: 'select', options: this.displayStatusToStatus, display: 'Status', link: 'status'},
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

    return FieldGroupMarkup.create(form, "Save Project", this);
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

      let post = '';
      if (snapshot.status.id === 'failed') {
        post = <i>Failed</i>;
      } else {
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
        post = <Request
                  parentElem={this}
                  name="activate_snapshot"
                  endpoint={endpoint}
                  method="post"
                  params={params}>
                  <Button type="blue">
                    <span>{action}</span>
                  </Button>
               </Request>;
      }
      let idlink = <a href={URI(`/snapshot/${snapshot.id}`)}>{snapshot.id}</a>;
      return [idlink, sha, <TimeText time={snapshot.dateCreated} />, post];
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
      selectedPlan: null,
    };
  },

  render: function() {
    let rows = [];
    let selectedPlan = this.state.selectedPlan;

    _.each(this.props.plans, plan => {
      let isSelected = selectedPlan === plan;
      let onClick = __ => {
        let newValue = isSelected ? null : plan;
        this.setState({selectedPlan: newValue});
      };

      var expandLabel = !isSelected ?  'Show Plan' : 'Hide Plan';

      var planName = <div>
        {plan.name} <a onClick={onClick}>{expandLabel}</a>
      </div>;

      let createTime = <TimeText time={plan.dateCreated} />
      let data = [planName, plan.status.name, createTime];
      let gridRow = new GridRow(data, false, false);
      rows.push(gridRow);
    });

    let planDetails = null;
    if (selectedPlan) {
      planDetails = <PlanDetailsWrapper className="indent" plan={selectedPlan} />
    }

    let content = <div>
        <Grid
             colnum={3}
             cellClasses={['wide', 'nowrap', 'nowrap']}
             data = {rows}
             headers={['Plan', 'Status', 'Created']}
           />
           {planDetails}
        </div>

    return content;
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
      options: `/api/0/plans/${this.props.plan.id}/options/`,
    });
  },

  render: function() {
    if (!api.isLoaded(this.state.options)) {
      return <APINotLoadedPage calls={this.state.options} />;
    }
    let options = this.state.options.getReturnedData();

    // Force a new PlanDetails when the selected plan changes, such that configuration changes
    let key = "planDetailsWrapper_" + this.props.plan.id;
    return <PlanDetails options={options} plan={this.props.plan} key={key} />;
  },
});

let PlanDetails = React.createClass({

  mixins: [React.addons.LinkedStateMixin],

  propTypes: {
    plan: PropTypes.object.isRequired,
    options: PropTypes.object.isRequired,
  },

  displayStatusToStatus: {
    'Active': 'active',
    'Inactive': 'inactive',
  },

  getInitialState: function() {
    return {
      createStepClicked: false,
      hasFormChanges: false,
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
    this.setState({hasFormChanges: false});
  },

  componentDidMount: function() {
    let project = this.props.project;
    this.setState({ name: this.props.plan.name,
                    status: this.props.plan.status.id,
                    expectTests: this.props.options['build.expect-tests'] === '1',
                    allowSnapshot: this.props.options['snapshot.allow'] === '1',
                  });
  },

  render: function() {
    let form = [
      { sectionTitle: 'Basics', fields: [
        {type: 'text', display: 'Name', link: 'name'},
        {type: 'select', options: this.displayStatusToStatus, display: 'Status', link: 'status'},
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

    let formMessages = [];
    let saveOptionsMessage = '';
    let savePlanMessage = '';
    if (!this.state.hasFormChanges) {
      if (this.state._postRequest_plan) {
        let result = this.state._postRequest_plan;
        if (result.condition === 'loaded')
          formMessages.push('Saved plan basics');
        else if (result.condition === 'error')
          formMessages.push('Failed to save plan basics: ' + result.response.responseText);
      }
      if (this.state._postRequest_options) {
        let result = this.state._postRequest_options;
        if (result.condition === 'loaded')
          formMessages.push('Saved plan options');
        else if (result.condition === 'error')
          formMessages.push('Failed to save plan options: ' + result.response.responseText);
      }
    }
    let fieldMarkup = FieldGroupMarkup.create(form, "Save Plan", this, formMessages);

    let stepMarkup = null;
    if (this.props.plan.steps.length > 0) {
      let step = this.props.plan.steps[0];
      stepMarkup = <StepDetails stepExists={true} step={step} />;
    } else if (this.state.createStepClicked) {
      let step = {'name': 'LXCBuildStep',
                  'implementation': 'changes.buildsteps.lxc.LXCBuildStep',
                  'options': { 'build.timeout': 0},
                  'data': 'Specify a configuration with JSON.',
                  };
      let onClick = _ => this.setState({ createStepClicked: false });
      stepMarkup = <StepDetails stepExists={false}
                                step={step}
                                plan={this.props.plan} />;
    } else {
      let onClick = _ => this.setState({ createStepClicked: true });
      stepMarkup = <Button onClick={onClick}>Create Step</Button>;
    }

    let rows = [[fieldMarkup, stepMarkup]];
    return <div className="marginLeftL marginRightL">
        <h1 className="marginBottomXS" >Plan Details - <span className="darkGray">{this.props.plan.name}</span></h1>
        <Grid
             colnum={2}
             cellClasses={['half projectDetailsCell', 'half projectDetailsCell']}
             data = {rows}
           />
       </div>
  },
});

let StepDetails = React.createClass({

  mixins: [React.addons.LinkedStateMixin],

  propTypes: {
    step: PropTypes.object.isRequired,
    stepExists: PropTypes.bool.isRequired,
    cancelCreateStep: PropTypes.func,
    plan: PropTypes.object,
  },

  getInitialState: function() {
    return {
    };
  },

  changesBuildStepImplementationFor: {
    'DefaultBuildStep': 'changes.buildsteps.default.DefaultBuildStep',
    'LXCBuildStep': 'changes.buildsteps.lxc.LXCBuildStep',
    'JenkinsBuildStep': 'changes.backends.jenkins.buildstep.JenkinsBuildStep',
    'JenkinsGenericBuildStep': 'changes.backends.jenkins.buildstep.JenkinsGenericBuildStep',
    'JenkinsTestCollectorBuildStep': 'changes.backends.jenkins.buildsteps.test_collector.JenkinsTestCollectorBuildStep',
  },

  saveSettings: function() {
    let state = this.state;
    let step_params = {
      'name': state.name,
      'build.timeout': state.timeout,
      'data': state.data,
      'implementation': state.implementation,
    };

    var endpoint;
    if (this.props.stepExists) {
      endpoint = '/api/0/steps/' + this.props.step.id + '/';
    } else {
      endpoint = '/api/0/plans/' + this.props.plan.id + '/steps/';
    }

    let endpoints = {
      '_postRequest_step': endpoint,
    };
    let params = {
      '_postRequest_step': step_params,
    };

    api.post(this, endpoints, params);
    this.setState({hasFormChanges: false});
  },

  componentDidMount: function() {
    let step = this.props.step;
    this.setState({ name: step.name,
                    timeout: step.options['build.timeout'],
                    data: step.data,
                    implementation: step.implementation,
                  });
  },

  render: function() {
    let step = this.props.step;

    let formMessages = [];
    if (!this.state.hasFormChanges) {
      if (this.state._postRequest_step) {
        let result = this.state._postRequest_step;
        if (result.condition === 'loaded')
          formMessages.push('Saved step');
        else if (result.condition === 'error')
          formMessages.push('Failed to save step: ' + result.response.responseText);
      }
    }
    let form = [
      {
        sectionTitle: step.name,
        fields: [
          {type: 'select', display: 'Implementation', link: 'implementation',
           options: this.changesBuildStepImplementationFor },
          {type: 'textarea', display: 'Config', link: 'data'},
          {type: 'text', display: 'Timeout', link: 'timeout'},
        ]
      },
    ];

    let del = <Request
                 parentElem={this}
                 name="deleteStep"
                 method="delete"
                 endpoint={`/api/0/steps/${step.id}/`}
                 promptText={`Delete ${step.name}?`}>
                   <Button className="marginLeftS">Delete Step</Button>
                </Request>;

    return FieldGroupMarkup.create(form, "Save Step", this, formMessages, [del]);
  },
});

let NewPlan = React.createClass({

  mixins: [React.addons.LinkedStateMixin],

  propTypes: {
    project: PropTypes.object.isRequired,
  },

  getInitialState: function() {
    return {
      'hasFormChanges': false,
      'error': null
    };
  },

  saveSettings: function() {
    let plan_params = {
      'name': this.state.name,
    };

    let project = this.props.project;
    let saveCallback = FieldGroupMarkup.redirectCallback(
      this, _ => {
        return URI(ChangesLinks.projectPlanAdminHref(project));
      });

    api.make_api_ajax_post(`/api/0/projects/${project.id}/plans/`, plan_params, saveCallback, saveCallback);
    this.setState({ hasFormChanges: false });
  },

  render: function() {
    let form = [
      { sectionTitle: '', fields: [
        {type: 'text', display: 'Name', link: 'name', placeholder: 'e.g. ' + this.props.project.slug},
        ]
      },
    ];

    return FieldGroupMarkup.create(form, "Create Plan", this, [this.state.error]);
  },
});

export default AdminProjectPage;
