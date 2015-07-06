import React from 'react';

import Grid from 'es6!display/grid';
import { StatusDot, status_dots } from 'es6!display/builds';
import SectionHeader from 'es6!display/section_header';
import ChangesPage from 'es6!display/page_chrome';
import NotLoaded from 'es6!display/not_loaded';
import { TimeText } from 'es6!display/time';
import { Menu1 } from 'es6!display/menus';

import { fetch_data } from 'es6!utils/data_fetching';
import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

var AllProjectsPage = React.createClass({

  getInitialState: function() {
    return {
      projectsStatus: 'loading',
      projectsData: null,
      projectsError: {},

      selectedItem: 'Latest Project Builds'
    }
  },

  componentDidMount: function() {
    var projects_endpoint = '/api/0/projects/?fetch_extra=1';

    fetch_data(this, {
      projects: projects_endpoint,
    });
  },

  render: function() {
    if (this.state.projectsStatus !== "loaded") {
      return <NotLoaded
        loadStatus={this.state.projectsStatus}
        errorData={this.state.projectsError}
      />;
    }
    var projects_data = this.state.projectsData;

    // render menu
    var menu_items = [
      'Latest Project Builds',
      'Projects By Repository',
      'Plans',
      'Plans by Type'
    ];

    var selected_item = this.state.selectedItem;

    var onClick = (item => {
      if (item === selected_item) {
        return;
      }
      this.setState({selectedItem: item});
    });

    var menu = <Menu1 
      items={menu_items} 
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
      case 'Plans by Type':
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
  renderDefault(projects_data) {
    var grid_data = _.map(projects_data, p => {
      var status_dot = null;
      if (p.lastBuild) {
        var status_dot = <StatusDot
          result={p.lastBuild.result.id}
        />;
      }

      return [
        status_dot,
        <a href={"/v2/project/" + p.slug}>{p.name}</a>
      ];
    });
    
    var headers = ['Status', 'Name'];
    var cellClasses = ['nowrap', 'wide'];

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
    var markup = [];
    var by_repo = _.groupBy(projects_data, p => p.repository.id);
    _.each(by_repo, repo_projects => {
      var header = <SectionHeader>
        {repo_projects[0].repository.url}
      </SectionHeader>;

      var rows = _.map(repo_projects, p => {
        var triggers = _.compact([
          p.options["phabricator.diff-trigger"] ? "Diffs" : "",
          p.options["build.commit-trigger"] ? "Commits" : ""
        ]).join(", ");
        
        var whitelist = "";
        if (p.options['build.file-whitelist']) {
          whitelist = _.map(
            p.options['build.file-whitelist'].match(/[^\r\n]+/g),
            l => <div>{l}</div>
          );
        }

        return [
          p.name, 
          triggers,
          p.options['build.branch-names'],
          whitelist
        ];
      });

      var headers = ['Name', 'Builds for', 'With branches', 'With paths'];
      var cellClasses = ['nowrap', 'nowrap', 'nowrap', 'wide'];

      markup.push(
        <div className="marginBottomL">
          {header}
          <Grid 
            data={rows} 
            headers={headers} 
            cellClasses={cellClasses} 
          />
        </div>
      );
    });
    
    return <div>{markup}</div>;
  },

  /*
   * Renders individual build plans for projects
   */
  renderPlans(projects_data) {
    var rows = [];
    _.each(projects_data, proj => {
      _.each(proj.plans, (plan, index) => {
        rows.push([
          (index === 0) ? proj.name : "",
          plan.name,
          plan.steps.length > 0 ? plan.steps[0].name : ""
        ]);
      });
    });

    // TODO: snapshot config?
    var headers = ['Project', 'Plan', 'Implementation'];
    var cellClasses = ['nowrap', 'wide', 'nowrap'];

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

    var markup = [];
    _.each(every_plan_type, type => {
      // find every plan that matches this type and render it
      var rows = [];
      _.each(projects_data, proj => {
        _.each(proj.plans, (plan, index) => {
          if (plan.steps.length > 0 && plan.steps[0].name === type) {
            rows.push([
              proj.name,
              plan.name,
            ]);
          }
        });
      });

      var headers = ['Project Name', 'Plan Name'];
      var cellClasses = ['nowrap', 'nowrap'];

      var header = <SectionHeader>
        {type} ({rows.length})
      </SectionHeader>;

      markup.push(
        <div className="marginBottomL">
          {header}
          <Grid 
            data={rows} 
            headers={headers} 
            cellClasses={cellClasses} 
          />
        </div>
      );
    });
    
    return markup;
  },
});

export default AllProjectsPage;
