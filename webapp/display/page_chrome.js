import React from 'react';
import moment from 'moment';

import APINotLoaded from 'es6!display/not_loaded';
import SectionHeader from 'es6!display/section_header';
import { Error } from 'es6!display/errors';
import { Grid } from 'es6!display/grid';
import { TimeText } from 'es6!display/time';

import * as api from 'es6!server/api';

import custom_content_hook from 'es6!utils/custom_content';
import { email_head } from 'es6!utils/utils';

var cx = React.addons.classSet;

var ChangesPage = React.createClass({

  propTypes: {
    // should we automatically add padding to the page content?
    bodyPadding: React.PropTypes.bool,
    // the first time you render the page with this set to true,
    // we record the time and show a widget with perf info in the header
    // TODO: handle transitions for a single-page app..
    isPageLoaded: React.PropTypes.bool,
    // If you're on a page linked to in the top bar, highlight it
    highlight: React.PropTypes.string,
    // we have to use position: fixed for some pages
    fixed: React.PropTypes.bool,
  },


  getInitialState: function() {
    return {
      adminMessage: null,
    }
  },

  getDefaultProps: function() {
    return {
      bodyPadding: true,
      isPageLoaded: true,
      fixed: false
    };
  },

  componentDidMount: function() {
    var messageEndpoint = '/api/0/messages/';
    api.fetch(this, {
      adminMessage: messageEndpoint,
    });
  },

  render: function() {
    if (!api.isLoaded(this.state.adminMessage)) {
      return <APINotLoaded state={this.state.adminMessage} />;
    }

    var message_markup = null;

    var message_data = this.state.adminMessage.getReturnedData();
    if (message_data && message_data.message) {
      var message_markup = <div className="persistentMessageHeader">
        {message_data.message}{"  - "}{message_data.user.email}
      </div>;
    }

    if (this.props.isPageLoaded) {
      // NOTE: once browsers support it, we could start using
      // window.performance.mark
      window.changesPageLoaded = window.changesPageLoaded ||
        new Date().getTime(); // We want to compare to this window.performance,
                              // so want to use new Date() rather than moment.
    }

    var style = this.props.bodyPadding ? {padding: 20} : {};

    return <div>
      {message_markup}
      <ChangesPageHeader highlight={this.props.highlight} fixed={this.props.fixed} />
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

  propTypes: {
    highlight: React.PropTypes.string, // see ChangesPage
    fixed: React.PropTypes.bool
  },

  render: function() {
    var feedback_href = custom_content_hook('feedbackHref');
    var feedback_link = null;
    if (feedback_href) {
      feedback_link = <a className="headerLinkBlock floatR"
        target="_blank"
        href={feedback_href}>
        Give Feedback!
      </a>;
    }

/* TODO:
        <a className="headerLinkBlock" href="/v2/nodes/">
          Machines
        </a>
*/

    var highlight = this.props.highlight;
    var my_changes_classes = cx({
      headerLinkBlock: true, headerHighlight: highlight === "My Changes"
    });

    var all_projects_classes = cx({
      headerLinkBlock: true, headerHighlight: highlight === "Projects"
    });

    /*
    var logo = <div
      className="headerBlock"
      style={{fontWeight: 900}}>
      Changes
    </div>;
    */

    var classes = cx({pageHeader: true, fixedPageHeader: this.props.fixed });
    return <div>
      <div className={classes}>
        <a className={my_changes_classes} href="/v2/">
          My Changes
        </a>
        <a className={all_projects_classes} href="/v2/projects/">
          Projects
        </a>
        <ChangesLogin />
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
      floatR: true,
      inlinePerfExpanded: this.state.expanded
    });

    return <div
      className={classes}
      onClick={onclick}
      style={{position: 'relative'}}>
      <div>
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
        // this just has to be monotonically increasing, so new Date is fine
        this.setState({lastUpdated: new Date().getTime()});
      }, 500);
    } else if (!is_expanded && this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  },

  // Add a custom content hook to allow an errors dashboard link to be added
  renderErrorsDashboardLink: function() {
    var errors_href = custom_content_hook('errorsHref');
    var errors_name = custom_content_hook('errorsName');
    if (!errors_href || !errors_name) {
      return <div />;
    }
    return <div className="marginTopM">
      <b>Link to Error Dashboard:{" "}</b>
      <a href={errors_href}>
        {errors_name}
      </a>
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

    var fmt_time = t => Math.round(t) + "ms";

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
        <div>{api_name}<div className="subText">{query_params}</div></div> :
        <div>{api_name}</div>;

      // url to trace api call
      var trace_href = api_has_query_params ?
        e.name + '&__trace__=1' :
        e.name + '?__trace__=1';
      var trace_link = <a href={trace_href} target="_blank">(trace)</a>;

      // make data
      data.push([name_markup, fmt_time(e.startTime), fmt_time(e.duration), trace_link]);
    });

    // Also add in built.js
    _.each(window.performance.getEntries(), e => {
      if (e.name.indexOf('built.js') > 0) {
        data.push([
          <em>Compiled JS</em>,
          <em>{fmt_time(e.startTime)}</em>,
          <em>{fmt_time(e.duration)}</em>,
          ''
        ]);
      }
    });

    var headers = ["API Name", "Sent At", "Duration", "Links"];
    return <Grid colnum={4} headers={headers} data={data} />;
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
      <div className="subText">
        <a href={release_href} target="_blank">
        {release_info.hash.substr(0, 7)}
        </a>
        {" "}committed{" "}
        <TimeText format="X" time={release_info['author_time']} />
        {" "}by{" "}
        {email_head(release_info['author_email'])}.
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

var ChangesLogin = React.createClass({

  // no properties

  render: function() {
    if (!window.changesAuthData || !window.changesAuthData.user) {
      var current_location = encodeURIComponent(window.location.href);
      var login_href = '/auth/login/?orig_url=' + current_location;
      return <a className="headerLinkBlock floatR" href={login_href}>
        Log in
      </a>;
    } else {
      return <div className="floatR">
        <a className="headerLinkBlock" href="/auth/logout?return=1">
          <i className="fa fa-sign-out"></i>
        </a>
      </div>;
    }
  }
});

export default ChangesPage;
