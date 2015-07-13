import React from 'react';

import Grid from 'es6!display/grid';
import { StatusDot, status_dots } from 'es6!display/builds';
import SectionHeader from 'es6!display/section_header';
import ChangesPage from 'es6!display/page_chrome';
import APINotLoaded from 'es6!display/not_loaded';
import { TimeText } from 'es6!display/time';
import { Menu1 } from 'es6!display/menus';

import * as api from 'es6!server/api';
import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

var AllProjectsPage = React.createClass({

  getInitialState: function() {
    return {
      projects: null,
      selectedItem: 'Latest Project Builds'
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
    var menu_items = [
      'Latest Project Builds',
      'Projects By Repository',
      'Plans',
      'Plans by Type'
    ];
    var selected_item = this.state.selectedItem;

    // TODO: can move this to Menu elements
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
    var rows = [];
    var by_repo = _.groupBy(projects_data, p => p.repository.id);
    _.each(by_repo, repo_projects => {
      var repo_url = repo_projects[0].repository.url;
      var repo_name = _.last(repo_url.split(/:|\//));
      var repo_markup = <div>
        <b>{repo_name}</b>
        <div className="subText">{repo_url}</div>
      </div>;

      var repo_rows = _.map(repo_projects, (p, index) => {
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
          index === 0 ? repo_markup : '',
          p.name, 
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
