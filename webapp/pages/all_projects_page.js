import React from 'react';

import { Grid, GridRow } from 'es6!display/grid';
import { BuildWidget, StatusDot, status_dots } from 'es6!display/builds';
import SectionHeader from 'es6!display/section_header';
import ChangesPage from 'es6!display/page_chrome';
import APINotLoaded from 'es6!display/not_loaded';
import { TimeText } from 'es6!display/time';
import { Menu1, MenuUtils } from 'es6!display/menus';

import * as api from 'es6!server/api';
import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

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

      expandedConfigs: {},
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
      return <APINotLoaded state={this.state.projects} />;
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
    
    return <ChangesPage>
      <SectionHeader>All Projects</SectionHeader>
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
      {this.renderProjectList(stale_list)}
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

        widget = <BuildWidget build={build} />;
        build_time = <TimeText 
          time={build.dateFinished || build.dateCreated} 
        />;
      }

      return [
        widget,
        build_time,
        p.name,
        [<a href={"/v2/project/" + p.slug}>Commits</a>,
         <a className="marginLeftS" href={"/v2/project/" + p.slug + "#ProjectDetails"}>
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
      var repo_name = _.last(_.compact(repo_url.split(/:|\//)));
      if (repo_projects.length > 1) {
        repo_name += ` (${repo_projects.length})`; // add # of projects
      }
      var repo_markup = <div>
        <b>{repo_name}</b>
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
          whitelist
        ];
      });
      rows = rows.concat(repo_rows);
    });
    
    var headers = ['Repo', 'Project', 'Builds for', 'With branches', 'With paths'];
    var cellClasses = ['nowrap', 'nowrap', 'nowrap', 'nowrap', 'wide'];

    return <div className="marginBottomL">
      <Grid 
        colnum={5}
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
            <b>{proj.name}{" ("}{num_plans}{")"}</b> :
            <b>{proj.name}</b>;
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
            <span className="marginRightL">{plan.steps[0].name}</span>,
            this.getSeeConfigLink(plan.id),
            <TimeText time={plan.dateModified} />
          ]);

          if (this.isConfigExpanded(plan.id)) {
            rows.push(this.getExpandedConfigRow(plan));
          }
        }
      });
    });

    // TODO: snapshot config?
    var headers = ['Project', 'Plan', 'Implementation', 'More', 'Modified'];
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
      .map(p => p.steps.length > 0 ? p.steps[0].name : "")
      .compact()
      .uniq()
      .sortBy(_.identity)
      .value();

    var rows_lists = [];
    _.each(every_plan_type, type => {
      // find every plan that matches this type and render it
      var plan_rows = [];
      _.each(projects_data, proj => {
        _.each(proj.plans, (plan, index) => {
          if (plan.steps.length > 0 && plan.steps[0].name === type) {
            plan_rows.push([null, proj.name, plan.name, this.getSeeConfigLink(plan.id)]);

            if (this.isConfigExpanded(plan.id)) {
              plan_rows.push(this.getExpandedConfigRow(plan));
            }
          }
        });
      });
      // add plan type label to first row
      plan_rows[0][0] = <b>{[type, " (", plan_rows.length, ")"]}</b>;
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
        {split_urls_for_display[url][0]}
        <span className="bb">{split_urls_for_display[url][1]}</span>
        {split_urls_for_display[url][2]}
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
      <div className="yellowPre marginBottomM">
        Note: this chart only shows explicitly-configured master urls. Here are
        the fallbacks we use when master is not configured.
        <div><b>fallback_url: </b>{(jenkins_fallback_data['fallback_url'] || "None")}</div>
        <div><b>fallback_cluster_machines: </b>{(jenkins_fallback_data['fallback_cluster_machines'] || "None")}</div>
      </div>
      <Grid 
        colnum={5}
        data={rows} 
        headers={headers} 
        cellClasses={cellClasses} 
      />
    </div>;
  },

  getSeeConfigLink: function(plan_id) {
    var onClick = ___ => {
      this.setState(
        utils.update_state_key(
          'expandedConfigs', 
          plan_id, 
          !this.state.expandedConfigs[plan_id])
      );
    }

    return <a onClick={onClick}>See Config</a>;
  },

  isConfigExpanded: function(plan_id) {
    return this.state.expandedConfigs[plan_id];
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
        <pre className="yellowPre">
          {plan.steps[0] && plan.steps[0].data}
        </pre>
        {build_timeout_markup}
      </div>
    );
  }
});

export default AllProjectsPage;
