import React from 'react';

import Grid from 'es6!display/grid';
import { BuildWidget, StatusDot, status_dots } from 'es6!display/builds';
import SectionHeader from 'es6!display/section_header';
import ChangesPage from 'es6!display/page_chrome';
import APINotLoaded from 'es6!display/not_loaded';
import { TimeText } from 'es6!display/time';
import { Menu1 } from 'es6!display/menus';

import * as api from 'es6!server/api';
import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

var AllProjectsPage = React.createClass({

  menuItems: [
    'Latest Project Builds',
    'Projects By Repository',
    'Plans',
    'Plans By Type'
  ],

  STALE_MAX_AGE: 60*60*24*7, // one week

  getInitialState: function() {
    return {
      projects: null,
      selectedItem: 'Latest Project Builds'
    }
  },

  componentWillMount: function() {
    // change the initial selected item if there's a hash in the url
    if (window.location.hash) {
      var hash_to_menu_item = {};
      _.each(this.menuItems, i => {
        // let's accept a bunch of hash variants
        hash_to_menu_item[i] = i;
        hash_to_menu_item[i.toLowerCase()] = i;
        hash_to_menu_item[i.replace(/ /g, "")] = i;
        hash_to_menu_item[i.toLowerCase().replace(/ /g, "")] = i;
      });

      var hash = window.location.hash.substring(1);
      if (hash_to_menu_item[hash]) {
        this.setState({
          selectedItem: hash_to_menu_item[hash]
        });
      }
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

    // TODO: can move this to Menu elements
    var onClick = (item => {
      if (item === selected_item) {
        return;
      }
      window.location.hash = item.replace(/ /g, "");
      this.setState({selectedItem: item});
    });

    var menu = <Menu1 
      items={this.menuItems} 
      selectedItem={selected_item} 
      onClick={onClick}
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
      default:
        throw 'unreachable';
    }
    
    return <ChangesPage>
      <SectionHeader>All Projects</SectionHeader>
      {menu}
      {content}
    </ChangesPage>;
  },

  /*
   * Default way to render projects. Shows the latest build.
   * TODO: do we have any stats we want to show?
   * TODO: more stuff
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
         <a className="marginLeftS" href={"/v2/project/" + p.slug + "#Details"}>
           Details
         </a>
        ],
      ];
    });
    
    var headers = ['Last Build', 'When', 'Name', 'Links'];
    var cellClasses = ['nowrap buildWidgetCell', 'nowrap', 'nowrap', 'wide'];

    return <Grid 
      data={grid_data} 
      headers={headers} 
      cellClasses={cellClasses} 
    />;
  },

  /*
   * Clusters projects together by repo
   */
  renderByRepo(projects_data) {
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
        data={rows} 
        headers={headers} 
        cellClasses={cellClasses} 
      />
    </div>;
  },

  /*
   * Renders individual build plans for projects
   */
  renderPlans(projects_data) {
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
        rows.push([
          proj_name,
          plan.name,
          plan.steps.length > 0 ? plan.steps[0].name : "",
          <TimeText time={plan.dateModified} />
        ]);
      });
    });

    // TODO: snapshot config?
    var headers = ['Project', 'Plan', 'Implementation', 'Modified'];
    var cellClasses = ['nowrap', 'nowrap', 'wide', 'nowrap'];

    return <Grid 
      data={rows} 
      headers={headers} 
      cellClasses={cellClasses} 
    />;
  },

  /*
   * Clusters build plans by type
   */
  renderPlansByType(projects_data) {
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
            plan_rows.push([null, proj.name, plan.name]);
          }
        });
      });
      // add plan type label to first row
      plan_rows[0][0] = <b>{[type, " (", plan_rows.length, ")"]}</b>;
      rows_lists.push(plan_rows);
    });
    
    var headers = ['Infrastructure', 'Project Name', 'Plan Name'];
    var cellClasses = ['nowrap', 'nowrap', 'nowrap'];

    return <Grid 
      data={_.flatten(rows_lists, true)}
      headers={headers} 
      cellClasses={cellClasses} 
     />;
  },
});

export default AllProjectsPage;
