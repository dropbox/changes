import React, { PropTypes } from 'react';
import ReactDOM from 'react-dom';

import APINotLoaded from 'es6!display/not_loaded';
import SectionHeader from 'es6!display/section_header';
import SimpleTooltip from 'es6!display/simple_tooltip';
import { Grid } from 'es6!display/grid';
import { TimeText } from 'es6!display/time';

import custom_content_hook from 'es6!utils/custom_content';
import { email_head } from 'es6!utils/utils';

import classNames from 'classnames';

export var ChangesPage = React.createClass({

  propTypes: {
    // should we automatically add padding to the page content?
    bodyPadding: PropTypes.bool,
    // the first time you render the page with this set to true,
    // we record the time and show a widget with perf info in the header
    // TODO: handle non full-page-transitions, once we add them
    isPageLoaded: PropTypes.bool,
    // If you're on a page linked to in the top bar, highlight it
    highlight: PropTypes.string,
    // we have to use position: fixed for some pages
    fixed: PropTypes.bool,
    // if present, we render a link to return to the old ui
    // some pages can disable the perf widget (since they continuously
    // live-update)
    widget: PropTypes.bool,
  },

  getDefaultProps: function() {
    return {
      bodyPadding: true,
      isPageLoaded: true,
      fixed: false,
      widget: true
    };
  },

  render: function() {
    var messageMarkup = null;
    if (window.changesMessageData && window.changesMessageData.message) {
      var messageData = window.changesMessageData;
      messageMarkup = <div className='persistentMessage'>
        {messageData.message}{"  - "}{messageData.user.email}
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
      {messageMarkup}
      <ChangesPageHeader
        highlight={this.props.highlight}
        fixed={this.props.fixed}
        widget={this.props.widget}
      />
      <div id="ChangesPageChildren" className="nonFixedClass" style={style}>
        {this.props.children}
      </div>
    </div>;
  },

  componentDidMount: function() {
    var node = ReactDOM.findDOMNode(this);

    var messageNode = node.getElementsByClassName('persistentMessage')[0];
    if (messageNode){
      var newMargin = messageNode.offsetHeight;

      // always fix nav bar if there's an admin message
      var navNode = node.getElementsByClassName('pageHeader')[0];
      if (navNode) {
        navNode.className += ' fixedClass';
      }

      // realign objects without fixed position
      var elementsWithTopMargins = document.getElementsByClassName('changeMarginAdminMsg');
      if (elementsWithTopMargins){
        for (var h  = 0; h < elementsWithTopMargins.length; h++){
          var oldMargin = parseInt(window.getComputedStyle(elementsWithTopMargins[h])['margin-top']);
          if (oldMargin > 0) {
            elementsWithTopMargins[h].style['margin-top'] = (oldMargin + newMargin) + "px";
          }
        }
      }

      // whatever the height of the message header is in px,
      // adjust every fixed-position object down by that amount
      var fixedElements = document.getElementsByClassName('fixedClass');
      if (fixedElements){
        for (var i = 0; i < fixedElements.length; i++){
          var oldTop = parseInt(window.getComputedStyle(fixedElements[i])['top']);
          fixedElements[i].style['top'] = (newMargin + oldTop) + "px";
        }
      }

      // every other high-level container which is non-fixed
      // needs to be realigned
      var affectedElements = document.getElementsByClassName('nonFixedClass');
      if (affectedElements){
        for (var j = 0; j < affectedElements.length; j++){
          affectedElements[j].style['margin-top'] = newMargin + "px";
        }
      }
    }
  }
});

export var APINotLoadedPage = React.createClass({

  propTypes: {
    // required, but this could be null
    calls: PropTypes.oneOfType([PropTypes.object, PropTypes.array])

    // ...
    // transfers other properties to rendered <ChangesPage />
  },

  render: function() {
    var { calls, ...props} = this.props;
    props['isPageLoaded'] = false;

    var content = this.props.fixed ?
      <div style={{marginTop: 30}}><APINotLoaded calls={calls} /></div> :
      <APINotLoaded calls={calls} />

    return <ChangesPage {...props}>
      {content}
    </ChangesPage>;
  }

});

/*
 * The header that shows up at the the top of every page. Decided against
 * using fixed positioning: its not important enough (if it were the primary
 * means of navigation on the page, I'd have used it.)
 */
var ChangesPageHeader = React.createClass({

  propTypes: {
    highlight: PropTypes.string, // see ChangesPage
    fixed: PropTypes.bool,
    widget: PropTypes.bool
  },

  getInitialState() {
    return {
      helpExpanded: false
    };
  },

  render() {
    var feedback_href = custom_content_hook('feedbackHref');
    var feedback_link = null;
    if (feedback_href) {
      feedback_link = <a className="headerLinkBlock floatR"
        target="_blank"
        href={feedback_href}>
        Give Feedback!
      </a>;
    }

    var learnMore = this.renderLearnMore();

    var foreign_api_header = null;

    if (window.changesGlobals['USE_ANOTHER_HOST']) {
      foreign_api_header =
        <div className="headerLinkBlock floatR green">
          <SimpleTooltip
           placement="bottom"
           label="It looks like your local configuration makes use of a non-local host for API calls.">
            <span style={{borderBottom: "1px dotted #777"}}>
              Foreign API
            </span>
          </SimpleTooltip>
        </div>;
    }

/* TODO:
        <a className="headerLinkBlock" href="/nodes/">
          Changes Internals
        </a>
*/

    var highlight = this.props.highlight;
    var my_changes_classes = classNames({
      headerLinkBlock: true, headerHighlight: highlight === "My Changes"
    });

    var all_projects_classes = classNames({
      headerLinkBlock: true, headerHighlight: highlight === "Projects"
    });

    var classes = classNames({pageHeader: true, fixedClass: this.props.fixed });
    return <div>
      <div className={classes}>
        <a className={my_changes_classes} href="/">
          My Changes
        </a>
        <a className={all_projects_classes} href="/projects/">
          Projects
        </a>
        <ChangesLogin />
        {this.props.widget ? <ChangesInlinePerf /> : null}
        {learnMore}
        {feedback_link}
        {foreign_api_header}
      </div>
    </div>;
  },

  renderLearnMore() {
    var learnMoreLinks = custom_content_hook('learnMoreLinks');
    if (!learnMoreLinks) {
      return null;
    }

    var onClick = (e) => {
      this.setState({
        helpExpanded: !this.state.helpExpanded
      });
    }

    var expandedContent = null;
    if (this.state.helpExpanded) {
      var linkMarkup = _.map(learnMoreLinks, (link, index) => {
        var className = index > 0 ? 'marginTopL' : '';
        return <div className={className}>
          <a className="learnMoreLink" href={link.href} target="_blank">
            <span className="learnMoreLinkTitle">{link.name}</span>
            <div className="learnMoreDesc">
              {link.desc}
            </div>
          </a> 
        </div>;
      });

      var expandedContent = <div className="learnMoreContent">
        {linkMarkup}
      </div>;
    }

    return <a className="learnMoreHeaderBlock headerLinkBlock floatR"
      target="_blank">
      <div onClick={onClick} className="learnMoreCaret">
        Learn More
        <i className="fa fa-caret-down" style={{marginLeft: 4}} />
      </div>
      {expandedContent}
    </a>;
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

    var classes = classNames({
      headerBlock: true,
      inlinePerf: true,
      floatR: true,
      inlinePerfExpanded: this.state.expanded
    });

    return <div
      className={classes}
      style={{position: 'relative'}}>
      <div 
        onClick={onclick}
        className="inlinePerfCaret">
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
        <TimeText format="X" time={release_info['commit_time']} />
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
      var admin_link = <a
          className="headerLinkBlock"
          href="/admin"
          title="Admin">
          <i className="fa fa-cog"></i>
        </a>;
      return <div className="floatR">
        {admin_link}
        <a
          className="headerLinkBlock"
          href="/auth/logout?return=1"
          title="Sign Out">
          <i className="fa fa-sign-out"></i>
        </a>
      </div>;
    }
  }
});
