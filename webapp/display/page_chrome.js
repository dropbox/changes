import React from 'react';
import Grid from 'es6!display/grid';
import SectionHeader from 'es6!display/section_header';
import { TimeText } from 'es6!display/time';
import _ from 'underscore';

import custom_content_hook from 'es6!utils/custom_content';
import { email_localpart } from 'es6!utils/utils';

var cx = React.addons.classSet;
var proptype = React.PropTypes;

// Exports ChangesPage. Helper classes: ChangesPageHeader, 
// ChangesInlinePerf

var ChangesPage = React.createClass({

  propTypes: {
    // should we automatically add padding to the page content?
    bodyPadding: proptype.bool,
    // the first time you render the page with this set to true,
    // we record the time and show a widget with perf info in the header
    // TODO: handle transitions for a single-page app..
    isPageLoaded: proptype.bool
  },

  getDefaultProps: function() {
    return { bodyPadding: true, isPageLoaded: true };
  },

  render: function() {
    if (this.props.isPageLoaded) {
      // NOTE: once browsers support it, we could start using 
      // window.performance.mark
      window.changesPageLoaded = window.changesPageLoaded || new Date().getTime();
    }

    var style = this.props.bodyPadding ? {padding: '10px'} : {};

    return <div>
      <ChangesPageHeader />
      <div style={style}>
        {this.props.children}
      </div>
    </div>;
  }
});

/*
 * The header that shows up at the the top of every page. Decided against 
 * using fixed positioning: its not important enough (if it were the primary
 * means of navigation on the page, I'd have used it.)
 */
var ChangesPageHeader = React.createClass({
  
  // no properties

  render: function() {
    var feedback_href = custom_content_hook('feedbackHref');
    var feedback_link = null;
    if (feedback_href) {
      feedback_link = <a className="headerLinkBlock"
        style={{float: 'right'}}
        target="_blank"
        href={feedback_href}>
        Give Feedback!
      </a>;
    }

    // Log In not implemented yet, graying it out
    return <div>
      <div className="pageHeader">
        <div className="headerBlock"><b>Changes</b></div>
        <a className="headerLinkBlock" href="/v2/">
          My Changes
        </a>
        <a className="headerLinkBlock" href="/v2/projects/">
          All Projects
        </a>
        <div className="headerBlock" style={{float: 'right', color: '#959ca1'}}>
          Log in
        </div>
        <ChangesInlinePerf />
        {feedback_link}
      </div>
    </div>;
  }
});

/*
 * Renders inline performance info. When clicked, expands to show other
 * info as well: api timings, the latest revision, and possibly a link 
 * to an internal error page.
 *
 * Technically, this component does a few interesting things:
 * - It consumes global info on render (window.changesPageLoaded, and
 *   the resource timing API)
 * - It uses setInterval to constantly update and rerender itself when 
 *   expanded.
 */
var ChangesInlinePerf = React.createClass({
  
  componentWillMount: function() {
    this.refreshTimer = null;
  },

  getInitialState: function() {
    return {
      expanded: false,
      // this is a monotonically increasing number (e.g. timestamps work.)
      // update this to trigger a live-update re-render of the latest
      // performance data
      lastUpdated: 0
    };
  },

  render: function() {
    // if the browser doesn't support PerformanceTiming, bail and
    // render nothing (not even the other useful info)
    // This will probably never happen, though...
    if (!window.performance || !window.performance.timing ||
        !window.performance.timing.navigationStart) {
      return <div />;
    }

    // render page load time once we have that info
    var perf_markup = '---';
    if (window.changesPageLoaded) {
      var load_time = window.changesPageLoaded - 
          window.performance.timing.navigationStart;
      perf_markup = `${load_time}ms`;
    }

    // render the dropdown box with more info if the user clicks on this tab
    // TODO: add some links for perf dashboards
    var expanded_info = null;
    if (this.state.expanded) {
      expanded_info = <div className="inlinePerfDropdown">
        <SectionHeader>API Call performance</SectionHeader>
        {this.renderResourceTiming()}
        {this.renderErrorsDashboardLink()}
        {this.renderReleaseInfo()}
      </div>;
    }

    this.updateTimers(this.state.expanded);

    var onclick = (e) => {
      this.setState({
        expanded: !this.state.expanded
      });
    }

    var classes = cx({
      headerBlock: true,
      inlinePerf: true,
      inlinePerfExpanded: this.state.expanded
    });

    return <div 
      className={classes}
      style={{float: 'right', position: 'relative'}}>
      <div onClick={onclick}>
        {perf_markup}
        <i className="fa fa-caret-down" style={{marginLeft: 4}} />
      </div>
      {expanded_info}
    </div>;
  },

  // When this widget is expanded, re-render it twice a second with the 
  // latest data
  updateTimers: function(is_expanded) {
    if (is_expanded && !this.refreshTimer) {
      // TODO: only when visible
      this.refreshTimer = setInterval(arg => {
        this.setState({lastUpdated: new Date().getTime()});
      }, 500);
    } else if (!is_expanded && this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  },

  // Add a custom content hook to allow an errors dashboard link to be added
  renderErrorsDashboardLink: function() {
    var errors_link = custom_content_hook('errorsLink');
    if (!errors_link) {
      return <div />;
    }
    return <div className="marginTopM">
      <b>Link to Error Dashboard:{" "}</b>
      {errors_link}
    </div>;
  },

  // Renders a table with perf data of all the ajax api calls we make
  renderResourceTiming: function() {
    // only a few browsers support resource timing right now. We could roll our
    // own version, but its most likely not worth the effort.
    if (!window.performance.getEntries) {
      return <div>
        This browser doesn{"'"}t support individual performance metrics 
        for resource requests.
      </div>;
    }

    var api_entries = _.chain(window.performance.getEntries())
      .filter(e => e.name.indexOf('api/0/') !== -1)
      .sortBy(e => e.startTime)
      .value();

    var data = [];
    _.each(api_entries, e => {
      // just grab the api portion of the url
      var api_name_start = e.name.indexOf('api/0/') + 'api/0/'.length;
      var api_name = e.name.substr(api_name_start);

      // and extract query params
      var api_has_query_params = api_name.indexOf('?') !== -1;
      var query_params = '';
      if (api_has_query_params) {
        [api_name, query_params] = api_name.split('?', 2);
      }

      var name_markup = api_has_query_params ?
        <div>{api_name}<div className="perfParams">{query_params}</div></div> :
        <div>{api_name}</div>;

      // url to trace api call
      var trace_href = api_has_query_params ? 
        e.name + '&__trace__=1' :
        e.name + '?__trace__=1';
      var trace_link = <a href={trace_href} target="_blank">(trace)</a>;

      // make data
      var fmt_time = t => Math.round(t) + "ms";
      data.push([name_markup, fmt_time(e.startTime), fmt_time(e.duration), trace_link]);
    });

    var headers = ["API Name", "Sent At", "Duration", "Links"];
    return <Grid headers={headers} data={data} />;
  }, 

  // Info about the latest revision in this changes deployment
  renderReleaseInfo: function() {
    if (!window.changesGlobals['RELEASE_INFO']) {
      return <div />;
    }

    var release_info = window.changesGlobals['RELEASE_INFO'];

    var release_href = "https://github.com/dropbox/changes/commit/" +
        release_info.hash;
    return <div className="marginTopM">
      <b>
        Latest Revision:
        {" "}
      </b>
      {release_info.subject}
      <div className="perfParams">
        <a href={release_href} target="_blank">
        {release_info.hash.substr(0, 7)}
        </a>
        {" "}committed{" "}
        <TimeText format="X" time={release_info['author_time']} />
        {" "}by{" "}
        {email_localpart(release_info['author_email'])}.
      </div>
    </div>;
  },

  componentWillUnmount: function() {
    // clear the timer, if in use (e.g. the widget is expanded)
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }
  }
});

export default ChangesPage;
