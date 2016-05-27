import React, { PropTypes } from 'react';

import ChangesLinks from 'es6!display/changes/links';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import { Grid, GridRow } from 'es6!display/grid';
import { SingleBuildStatus } from 'es6!display/changes/builds';
import { TimeText, display_duration_pieces } from 'es6!display/time';
import { WaitingLiveText } from 'es6!display/changes/build_text';
import { get_runnable_condition,
         get_runnable_condition_color_cls,
         is_waiting } from 'es6!display/changes/build_conditions';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

// how often to hit the api server for updates
const POLL_INTERVAL = 10000;

/*
 * Modern query params:
 * - branch: select branch to display.
 * - project: pass multiple times to select projects to display. The value
 *   should be a project slug. All projects should be for the same repo.
 *
 * Antiquated query params: main (multiple times)
 * - The first main parameter determines the list of commits to show.
 *   Additional main parameters will show latest builds for that commit.
 * - A parameter can be just a project slug, or slug::branch.
 */
var PusherPage = React.createClass({

  getInitialTitle() {
    return 'Dashboard';
  },

  getInitialState() {
    var endpoints = this.getEndpoints();

    var state = {};
    _.each(_.keys(endpoints), key => {
      state[key] = null;
    });
    return state;
  },

  componentDidMount() {
    api.fetch(this, this.getEndpoints());

    this.updateInProgress = false;
    this.refreshTimer = window.setInterval(__ => {
      if (!this.isMounted()) {
        return;
      }
      this.liveUpdate();
    }, POLL_INTERVAL);
  },

  render() {
    if (this.updateInProgress) {
      if (api.allLoaded(_.values(this.state.liveUpdate))) {
        this.updateInProgress = false;
        utils.async(__ => {
          var emptyLiveUpdate = _.mapObject(this.getEndpoints(), (v, k) => null);
          this.setState(_.extend(
            {liveUpdate: emptyLiveUpdate},
            this.state.liveUpdate));
        });
      }
    }

    var [slugs, branch] = this.getSlugsAndBranch();
    var endpoints = this.getEndpoints();
    var apiResponses = _.map(endpoints, (v, k) => this.state[k]);

    if (!api.allLoaded(apiResponses)) {
      return <APINotLoadedPage calls={apiResponses} widget={false} />; 
    }

    // Adding key=current timestamp forces us to unmount/remount
    // PusherPageContent every re-render. This seems to prevent crazy memory
    // leaks, albeit at the cost of slightly less responsiveness (which is fine
    // for a dashboard.) I think I could solve this in a more sophisticated
    // way, but this is fine for now.
    return <ChangesPage widget={false}>
      <PusherPageContent
        slugs={slugs}
        branch={branch}
        fetchedState={this.state}
        key={+Date.now()}
      />
    </ChangesPage>;
  },

  getSlugsAndBranch() {
    var queryParams = URI(window.location.href).search(true);

    var slugs, branch;
    if (queryParams['project']) {
      // Modern parameters.
      slugs = queryParams['project'];
      if (!_.isArray(slugs)) {
        slugs = [slugs];
      }
      if (queryParams['branch']) {
        branch = queryParams['branch'];
      }
    } else {
      // Antiquated parameters.
      var mains = queryParams['main'];
      if (!_.isArray(mains)) {
        mains = [mains];
      }
      slugs = [];
      _.each(mains, main => {
        let [slug, temp_branch] = main.split('::');
        slugs.push(slug);
        if (!branch && temp_branch) {
          branch = temp_branch;
        }
      });
    }

    return [slugs, branch];
  },

  getEndpoints() {
    var queryParams = URI(window.location.href).search(true);
    let per_page = '50';
    if (queryParams['per_page']) {
      per_page = queryParams['per_page'];
    }

    var [slugs, branch] = this.getSlugsAndBranch();

    var endpoints = {};
    _.each(slugs, slug => {
      endpoints[slug] = URI(`/api/0/projects/${slug}/commits/`)
        .query({ all_builds: 1, branch: branch, per_page: per_page })
        .toString();
    });
    return endpoints;
  },

  liveUpdate() {
    // we'll make new API calls inside of liveUpdate. Once they've all
    // finished, we'll use setState to copy them over
    this.updateInProgress = true;
    this.setState({
      liveUpdate: _.mapObject(this.getEndpoints(), (v, k) => null)
    });

    api.fetchMap(this, 'liveUpdate', this.getEndpoints());
  },

  componentWillUnmount() {
    // clear the timer, if in use (e.g. the widget is expanded)
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }
  }
});


var PusherPageContent = React.createClass({
  
  propTypes: {
    slugs: PropTypes.array.isRequired,
    branch: PropTypes.string.isRequired,
  },

  getInitialState() { return {}; },

  render() {
    var slugs = this.props.slugs;
    var totalProjectCount = slugs.length;

    // we want to map slugs to project data (e.g. so we know the name of the
    // project. This is buried within each buld
    var projectData = {};

    var commitLists = {};
    _.each(slugs, proj => {
      commitLists[proj] = this.props.fetchedState[proj].getReturnedData();
    });

    // I don't want to write anything too complicated, so here's what we'll do:
    // we'll use the first "main" project as the source of truth for revisions,
    // and augment it with displaying builds from other projects.
    var rows = _.map(commitLists[slugs[0]], baseCommit => {
      var everyCommit = {};
      _.each(commitLists, (commitList, proj) => {
        _.each(commitList, commitInList => {
          if (commitInList.sha === baseCommit.sha) {
            everyCommit[proj] = commitInList;
          }
        });
      });

      var initialCells = [];
      _.each(slugs, proj => {
        if (!everyCommit[proj]) {
          initialCells.push(null);
          return;
        }

        var commit = everyCommit[proj];
        var sortedBuilds = _.sortBy(commit.builds, b => b.dateCreated).reverse();
        var lastBuild = _.first(sortedBuilds);
        if (lastBuild) {
          if (lastBuild.project) {
            projectData[lastBuild.project.slug] = lastBuild.project;
          }
          var duration = null;
          if (is_waiting(get_runnable_condition(lastBuild))) {
            duration = <WaitingLiveText runnable={lastBuild} text={false} />;
          } else {
            var pieces = _.chain(display_duration_pieces(lastBuild.duration / 1000))
              .filter(p => p)
              .map(p => p.replace(/[dmsh]/, ''))
              .value();

            duration = pieces.join(":");
          }
            
          var colorCls = get_runnable_condition_color_cls(get_runnable_condition(lastBuild));
          var durationStyle = {
            display: 'inline-block',
            position: 'relative',
            top: -2,
          };

          initialCells.push(
            <div>
              <div className="inlineBlock">
                <SingleBuildStatus
                  build={lastBuild}
                  parentElem={this}
                />
              </div>
              <a 
                href={ChangesLinks.buildHref(lastBuild)}
                className={colorCls} 
                style={durationStyle}>
                {duration}
              </a>
            </div>
          );
        } else {
          initialCells.push(null);
        }
      });

      // TODO: add the skip the queue indicator to this page (for consistency,
      // if nothing else)
      var title = utils.truncate(utils.first_line(baseCommit.message));

      let cells = initialCells.concat([
        title,
        ChangesLinks.author(baseCommit.author),
        ChangesLinks.phabCommit(baseCommit),
        <span><TimeText time={baseCommit.dateCommitted} /></span>
      ]);
      return new GridRow(baseCommit.sha, cells);
    });

    var projectHeaders = _.map(slugs, proj => {
      var name = utils.truncate(
        (projectData[proj] && projectData[proj].name) || proj,
        20);
      return <div className="pusherProjectHeader">
                <div className="projectName">{name}</div>
             </div>;
    });

    var headers = projectHeaders.concat([
      'Name',
      'Author',
      'Commit',
      'Committed'
    ]);

    var classHeaders = _.map(slugs, proj => 'nowrap buildWidgetCell');
    var cellClasses = classHeaders.concat([
      'wide',
      'nowrap',
      'nowrap',
      'nowrap'
    ]);

    return <div>
      <Grid
        colnum={4 + totalProjectCount}
        cellClasses={cellClasses}
        headers={headers}
        data={rows}
      />
    </div>;
  },
});

export default PusherPage;
