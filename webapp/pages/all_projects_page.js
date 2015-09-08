import React, { PropTypes } from 'react';
import moment from 'moment';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesPage from 'es6!display/page_chrome';
import DisplayUtils from 'es6!display/changes/utils';
import SectionHeader from 'es6!display/section_header';
import { Grid, GridRow } from 'es6!display/grid';
import { Menu1, MenuUtils } from 'es6!display/menus';
import { SingleBuildStatus } from 'es6!display/changes/builds';
import { TimeText } from 'es6!display/time';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

var AllProjectsPage = React.createClass({

  menuItems: [
    'Latest Project Builds',
    'Projects By Repository',
    'Plans',
    'Plans By Type',
    'Jenkins Plans By Master',
  ],

  STALE_MAX_AGE: 60*60*24*7, // one week

  getInitialState: function() {
    return {
      projects: null,
      selectedItem: 'Latest Project Builds',

      expandedConfigsInPlans: {},
      expandedConfigsInPlansByType: {},
    }
  },

  componentWillMount: function() {
    var selected_item_from_hash = MenuUtils.selectItemFromHash(
      window.location.hash, this.menuItems);

    if (selected_item_from_hash) {
      this.setState({ selectedItem: selected_item_from_hash });
    }
  },

  componentDidMount: function() {
    api.fetch(this, {
      projects: '/api/0/projects/?fetch_extra=1'
    });
  },

  render: function() {
    if (!api.isLoaded(this.state.projects)) {
      return <APINotLoaded state={this.state.projects} isInline={false} />;
    }
    var projects_data = this.state.projects.getReturnedData();

    // render menu
    var selected_item = this.state.selectedItem;

    var menu = <Menu1
      items={this.menuItems}
      selectedItem={selected_item}
      onClick={MenuUtils.onClick(this, selected_item)}
    />;

    // TODO: what is the snapshot.current option and should I display it?
    // TODO: ordering
    var content = null;
    switch (selected_item) {
      case 'Latest Project Builds':
        content = this.renderDefault(projects_data);
        break;
      case 'Projects By Repository':
        content = this.renderByRepo(projects_data);
        break;
      case 'Plans':
        content = this.renderPlans(projects_data);
        break;
      case 'Plans By Type':
        content = this.renderPlansByType(projects_data);
        break;
      case 'Jenkins Plans By Master':
        content = this.renderJenkinsPlansByMaster(projects_data);
        break;
      default:
        throw 'unreachable';
    }

    return <ChangesPage highlight="Projects">
      <SectionHeader>Projects</SectionHeader>
      {menu}
      <div className="marginTopM">{content}</div>
    </ChangesPage>;
  },

  /*
   * Default way to render projects. Shows the latest build.
   * TODO: do we have any stats we want to show?
   */
  renderDefault: function(projects_data) {
    var list = [], stale_list = [];
    _.each(projects_data, p => {
      var is_stale = false;
      if (p.lastBuild) {
        var age = moment.utc().format('X') - moment.utc(p.lastBuild.dateCreated).format('X');
        // if there's never been a build for this project, let's not consider
        // it stale
        is_stale = age > this.STALE_MAX_AGE;
      }
      !is_stale ? list.push(p) : stale_list.push(p);
    });

    var stale_header = stale_list ?
      <SectionHeader className="marginTopL">Stale Projects (>1 week)</SectionHeader> :
      null;

    return <div>
      {this.renderProjectList(list)}
      {stale_header}
      <div className="bluishGray">
        {this.renderProjectList(stale_list)}
      </div>
    </div>;
  },

  renderProjectList: function(projects_data) {
    if (_.isEmpty(projects_data)) {
      return null;
    }

    var grid_data = _.map(projects_data, p => {
      var widget = null, build_time = null;
      if (p.lastBuild) {
        var build = p.lastBuild;

        widget = <SingleBuildStatus build={build} parentElem={this} />;
        build_time = <TimeText
          time={build.dateFinished || build.dateCreated}
        />;
      }

      return [
        widget,
        build_time,
        p.name,
        [<a href={"/v2/project/" + p.slug}>Commits</a>,
         <a className="marginLeftM" href={"/v2/project/" + p.slug + "#Details"}>
           Details
         </a>
        ],
        p.options["project.notes"]
      ];
    });

    var headers = ['Last Build', 'When', 'Name', 'Links', 'Notes'];
    var cellClasses = ['nowrap buildWidgetCell', 'nowrap', 'nowrap', 'nowrap', 'wide'];

    return <Grid
      colnum={5}
      data={grid_data}
      headers={headers}
      cellClasses={cellClasses}
    />;
  },

  /*
   * Clusters projects together by repo
   */
  renderByRepo: function(projects_data) {
    var rows = [];
    var by_repo = _.groupBy(projects_data, p => p.repository.id);
    _.each(by_repo, repo_projects => {
      var repo_url = repo_projects[0].repository.url;
      var repo_name = DisplayUtils.getShortRepoName(repo_url);
      if (repo_projects.length > 1) {
        repo_name += ` (${repo_projects.length})`; // add # of projects
      }
      var repo_markup = <div>
        <span className="lb">{repo_name}</span>
        <div className="subText">{repo_url}</div>
      </div>;

      var repo_rows = _.map(repo_projects, (p, index) => {
        var triggers = "Never";
        if (p.options["phabricator.diff-trigger"] &&
            p.options["build.commit-trigger"]) {
          triggers = "Diffs and Commits";
        } else if (p.options["phabricator.diff-trigger"]) {
          triggers = "Only Diffs";
        } else if (p.options["build.commit-trigger"]) {
          triggers = "Only Commits";
        }

        var whitelist = "";
        if (p.options['build.file-whitelist']) {
          whitelist = _.map(
            utils.split_lines(p.options['build.file-whitelist']),
            l => <div>{l}</div>
          );
        }

        return [
          index === 0 ? repo_markup : '',
          <a href={"/v2/project/" + p.slug}>{p.name}</a>,
          triggers,
          p.options['build.branch-names'],
          whitelist,
          <TimeText time={p.dateCreated} />
        ];
      });
      rows = rows.concat(repo_rows);
    });

    var headers = ['Repo', 'Project', 'Builds for', 'With branches', 'With paths', 'Created'];
    var cellClasses = ['nowrap', 'nowrap', 'nowrap', 'nowrap', 'wide', 'nowrap'];

    return <div className="marginBottomL">
      <Grid
        colnum={6}
        data={rows}
        headers={headers}
        cellClasses={cellClasses}
      />
    </div>;
  },

  /*
   * Renders individual build plans for projects
   */
  renderPlans: function(projects_data) {
    var rows = [];
    _.each(projects_data, proj => {
      var num_plans = proj.plans.length;
      _.each(proj.plans, (plan, index) => {
        var proj_name = "";
        if (index === 0) {
          var proj_name = (num_plans > 1) ?
            <span className="lb">{proj.name}{" ("}{num_plans}{")"}</span> :
            <span className="lb">{proj.name}</span>;
        }

        if (!plan.steps[0]) {
          rows.push([
            proj_name,
            plan.name,
            '',
            '',
            <TimeText time={plan.dateModified} />
          ]);
        } else {
          rows.push([
            proj_name,
            plan.name,
            <span className="marginRightL">{this.getStepType(plan.steps[0])}</span>,
            this.getSeeConfigLink(plan.id, 'plans'),
            <TimeText time={plan.dateModified} />
          ]);

          if (this.isConfigExpanded(plan.id, 'plans')) {
            rows.push(this.getExpandedConfigRow(plan));
          }
        }
      });
    });

    // TODO: snapshot config?
    var more_link = <span>More{" "}
      <span style={{fontWeight: 'normal'}}>
        {"("}{this.getExpandAllLink('plans')}{")"}
      </span>
    </span>;
    var headers = ['Project', 'Plan', 'Implementation', more_link, 'Modified'];
    var cellClasses = ['nowrap', 'nowrap', 'nowrap', 'wide', 'nowrap'];

    return <Grid
      colnum={5}
      data={rows}
      headers={headers}
      cellClasses={cellClasses}
    />;
  },

  /*
   * Clusters build plans by type
   */
  renderPlansByType: function(projects_data) {
    var every_plan = _.flatten(
      _.map(projects_data, p => p.plans)
    );

    var every_plan_type = _.chain(every_plan)
      .map(p => p.steps.length > 0 ? this.getStepType(p.steps[0]) : "")
      .compact()
      .uniq()
      // sort, hoisting build types starting with [LXC] to the top
      .sortBy(t => t.charAt(0) === "[" ? "0" + t : t)
      .value();

    var rows_lists = [];
    _.each(every_plan_type, type => {
      // find every plan that matches this type and render it
      var plan_rows = [];
      _.each(projects_data, proj => {
        _.each(proj.plans, (plan, index) => {
          if (plan.steps.length > 0 && this.getStepType(plan.steps[0]) === type) {
            plan_rows.push([
              null,
              proj.name,
              plan.name,
              this.getSeeConfigLink(plan.id, 'plansByType')
            ]);

            if (this.isConfigExpanded(plan.id, 'plansByType')) {
              plan_rows.push(this.getExpandedConfigRow(plan));
            }
          }
        });
      });
      // add plan type label to first row
      plan_rows[0][0] = <span className="lb">
        {[type, " (", plan_rows.length, ")"]}
      </span>;
      rows_lists.push(plan_rows);
    });

    var headers = ['Infrastructure', 'Project Name', 'Plan Name', 'More'];
    var cellClasses = ['nowrap', 'nowrap', 'nowrap', 'nowrap'];

    return <Grid
      colnum={4}
      data={_.flatten(rows_lists, true)}
      headers={headers}
      cellClasses={cellClasses}
     />;
  },

  renderJenkinsPlansByMaster: function(projects_data) {
    // keys are jenkins master urls. Values are two lists (master/diff) each of
    // plans (since we have a separate jenkins_diff_urls)
    var plans_by_master = {};
    var jenkins_fallback_data = {};

    // ignore trailing slash for urls
    var del_trailing_slash = url => url.replace(/\/$/, '');

    _.each(projects_data, proj => {
      _.each(proj.plans, plan => {
        plan.project = proj;

        // is there a plan?
        if (!plan.steps[0]) { return; }
        // is it a jenkins plan?
        if (plan.steps[0].name.toLowerCase().indexOf('jenkins') === -1) {
          return;
        }

        if (plan['jenkins_fallback']) {
          jenkins_fallback_data = plan['jenkins_fallback'];
          jenkins_fallback_data['fallback_cluster_machines'] =
            jenkins_fallback_data['fallback_cluster_machines'] ?
            JSON.stringify(jenkins_fallback_data['fallback_cluster_machines']) :
            "None";
        }

        var data = JSON.parse(plan.steps[0].data);

        if (data['jenkins_url']) {
          _.each(utils.ensureArray(data['jenkins_url']), u => {
            u = del_trailing_slash(u);
            plans_by_master[u] = plans_by_master[u] || {};
            plans_by_master[u]['master'] = plans_by_master[u]['master'] || [];
            plans_by_master[u]['master'].push(plan);
          });
        }
        if (data['jenkins_diff_url']) {
          _.each(utils.ensureArray(data['jenkins_diff_url']), u => {
            u = del_trailing_slash(u);
            plans_by_master[u] = plans_by_master[u] || {};
            plans_by_master[u]['diff'] = plans_by_master[u]['diff'] || [];
            plans_by_master[u]['diff'].push(plan);
          });
        }
      });
    });

    var split_urls_for_display = utils.split_start_and_end(
      _.keys(plans_by_master));

    var rows = [];
    _.each(_.keys(plans_by_master).sort(), url => {
      var val = plans_by_master[url];
      val.master = val.master || [];
      val.diff = val.diff || [];

      var is_first_row = true;
      var first_row_text = <span className="paddingRightM">
        <a className="subtle" href={url} target="_blank">
          {split_urls_for_display[url][0]}
          <b>{split_urls_for_display[url][1]}</b>
          {split_urls_for_display[url][2]}
        </a>
        {" ("}{val.master.length}{"/"}{val.diff.length}{")"}
      </span>;

      _.each(val.master, (plan, index) => {
        rows.push([
          is_first_row ? first_row_text : '',
          index === 0 ? <span className="paddingRightM">Anything</span> : '',
          plan.name,
          plan.project.name,
          <TimeText time={plan.dateModified} />
        ]);
        is_first_row = false;
      });

      _.each(val.diff, (plan, index) => {
        rows.push([
          is_first_row ? first_row_text : '',
          index === 0 ? <span className="paddingRightM">Diffs-only</span> : '',
          plan.name,
          plan.project.name,
          <TimeText time={plan.dateModified} />
        ]);
        is_first_row = false;
      });
    });

    var headers = ['Master', 'Used for', 'Plan', 'Project', 'Modified'];
    var cellClasses = ['nowrap', 'nowrap', 'nowrap', 'wide', 'nowrap'];

    return <div>
      <div className="defaultPre marginBottomM">
        Note: this chart only shows explicitly-configured master urls. Here are
        the fallbacks we use when master is not configured.
        <div><b>fallback_url: </b>{(jenkins_fallback_data['fallback_url'] || "None")}</div>
        <div><b>fallback_cluster_machines: </b>
          {jenkins_fallback_data['fallback_cluster_machines']}
        </div>
      </div>
      <Grid
        colnum={5}
        data={rows}
        headers={headers}
        cellClasses={cellClasses}
      />
    </div>;
  },

  getSeeConfigLink: function(plan_id, chart_name) {
    var state_key = this.getConfigStateKey(chart_name);

    var onClick = ___ => {
      this.setState(
        utils.update_key_in_state_dict(
          state_key,
          plan_id,
          !this.state[state_key][plan_id])
      );
    }

    var text = this.state[state_key][plan_id] ?
      'Hide Config' : 'See Config';
    return <a onClick={onClick}>{text}</a>;
  },

  getExpandAllLink: function(chart_name) {
    var state_key = this.getConfigStateKey(chart_name);

    var onClick = ___ => {
      if (this.state[state_key]['all']) {
        // delete all variables that expand a config
        this.setState({ [ state_key ]: {}});
      } else {
        this.setState(
          utils.update_key_in_state_dict(state_key, 'all', true)
        );
      }
    };

    var text = this.state[state_key]['all'] ?
      'Collapse All' : 'Expand All';

    return <a onClick={onClick}>{text}</a>;
  },

  isConfigExpanded: function(plan_id, chart_name) {
    var state_key = this.getConfigStateKey(chart_name);

    return this.state[state_key][plan_id] || this.state[state_key]['all'];
  },

  getConfigStateKey: function(chart_name) {
    switch (chart_name) {
      case 'plans': return 'expandedConfigsInPlans';
      case 'plansByType': return 'expandedConfigsInPlansByType';
      default: throw `unknown chart name ${chart_name}`;
    };
  },

  getExpandedConfigRow: function(plan) {
    var build_timeout = plan.steps[0].options['build.timeout'];
    var build_timeout_markup = null;
    if (build_timeout !== undefined) {
      build_timeout_markup = [
        <span className="lb">Build Timeout: </span>,
        build_timeout
      ];
    }

    return GridRow.oneItem(
      <div>
        <pre className="defaultPre">
          {plan.steps[0] && plan.steps[0].data}
        </pre>
        {build_timeout_markup}
      </div>
    );
  },

  getStepType: function(step) {
    var is_lxc = false;
    _.each(utils.split_lines(step.data), line => {
      // look for a "build_type": "lxc" line
      if (line.indexOf("build_type") >= 0 && line.indexOf("lxc") >= 0) {
        is_lxc = true;
      }
    });

    var is_jenkins_lxc = is_lxc && step.name.indexOf("Jenkins") >= 0;
    return is_jenkins_lxc ?
      "[LXC] " + step.name :
      step.name;
  }

});

export default AllProjectsPage;
