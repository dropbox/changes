import React, { PropTypes } from 'react';

import ChangesLinks from 'es6!display/changes/links';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import { Error, AjaxError } from 'es6!display/errors';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

// Disable log altogether lines >= 40K.
var MAX_LOG_LINES = 40960;

// how often to hit the api server for updates
var POLL_INTERVAL = 1000;

function logging_endpoint(jobID, logsourceID, offset = null) {
  var params = { limit: 0 };
  if (offset) {
    params.offset = offset;
  }

  return URI(`/api/0/jobs/${jobID}/logs/${logsourceID}`)
    .setSearch(params)
    .toString();
}

/**
 * Log that automatically tails and gets the latest updates. This page is just
 * a wrapper around LogComponent that fetches the initial data and renders the
 * page chrome
 */
var LogPage = React.createClass({

  getInitialState: function() {
    return {
      initialLog: null,
      build: null
    }
  },

  componentDidMount: function() {
    var jobID = this.props.jobID;
    var logsourceID = this.props.logsourceID;

    api.fetch(this, {
      initialLog: logging_endpoint(jobID, logsourceID),
      build: `/api/0/builds/${this.props.buildID}`
    });
  },

  render: function() {
    if (!api.allLoaded([this.state.initialLog, this.state.build])) {
      return <APINotLoadedPage
        calls={[this.state.initialLog, this.state.build]}
      />;
    }

    var parentJobstep = this.state.initialLog.getReturnedData().source.step;
    utils.setPageTitle(`Logs - ${parentJobstep.node.name}`);

    return <ChangesPage fixed={true}>
      <LogComponent
        initialLog={this.state.initialLog}
        jobID={this.props.jobID}
        build={this.state.build}
        logsourceID={this.props.logsourceID}
      />
    </ChangesPage>;
  }
});

var LogComponent = React.createClass({

  componentWillMount: function() {
    this.refreshTimer = null;
    this.initialRender = true;  // on the initial render only, scroll to bottom
  },

  getInitialState: function() {
    return {
      // these don't use APIResponse/api.fetch...we directly populate them
      newLogs: [],
      updateError: null // if we get an error back, store the ajax response here
    }
  },

  componentDidMount: function() {
    // kick off our polling logic: a series of setTimeouts that update state as
    // new data comes in
    this.refreshTimer = window.setTimeout(__ => {
      if (!this.isMounted()) {
        return;
      }
      this.pollForUpdates();
    }, POLL_INTERVAL);

    // scroll to the bottom after our first render
    if (this.initialRender) {
      this.initialRender = false;
      this.scrollToBottom();
    }
  },

  componentWillUnmount: function() {
    // clear the timer, if in use (e.g. the widget is expanded)
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }
  },

  render: function() {
    var initialLog = this.props.initialLog;
    var newLogs = this.state.newLogs;

    var apiCallsToRender = [initialLog.getReturnedData()].concat(
      this.state.newLogs);

    var tooManyLines = false;
    var isFinished = false;
    var lines = [];
    _.each(apiCallsToRender, apiCall => {
      if (apiCall.source.step.status.id === 'finished') {
        isFinished = true;
      }
      _.each(apiCall.chunks, chunk => {
        _.each(chunk.text.split("\n"), line => {
          if (lines.length >= MAX_LOG_LINES) {
            tooManyLines = true;
            return;
          }
          lines.push(
            <div
              className="line"
              // the backend sends us pre-escaped markup, I think for coloring
              dangerouslySetInnerHTML={{__html: line}}
            />
          );
        });
      });
    });

    this.state.linesRendered = lines.length;

    var otherContent = [];
    if (this.state.updateError) {
      otherContent.push(<AjaxError response={this.state.updateError} />);
    }

    if (tooManyLines) {
      // TODO: could add a link to the raw log here
      otherContent.push(
        <Error>
          Truncating display: we render at most {MAX_LOG_LINES} lines
        </Error>
      );
    } 
    
    if (!isFinished && otherContent.length === 0) {
      // if we're still waiting on content, render an old-school blinking
      // terminal cursor
      otherContent.push(
        <div className="blink">
          {"\u2588"}
        </div>
      );
    }

    return <div className="logFile">
      {this.renderTopRightBox()}
      {lines}
      {otherContent}
    </div>;
  },

  renderTopRightBox() {
    var build = this.props.build.getReturnedData();

    var header = null;
    if (!build.source.patch) {
      header = <div className="paddingBottomXS">
        {build.source.revision.sha.substring(0,7)}{": "}
        {utils.truncate(utils.first_line(build.source.revision.message), 40)}
      </div>;
    } else if (build.source.patch && build.source.data['phabricator.revisionID']) {
      header = <div className="paddingBottomXS">
        {'D' + build.source.data['phabricator.revisionID']}
        {': '}
        {utils.truncate(utils.first_line(build.message), 40)}
      </div>;
    }

    return <div className="logReturnLink">
      {header}
      <div>
        {this.state.linesRendered} lines
        {" "}
        &middot;
        {" "}
        <a href={ChangesLinks.buildHref(build)}>
          Return to build
        </a>
      </div>
    </div>;
  },

  componentWillUpdate: function() {
    // keep us scrolled all the way at the bottom if we're already there
    this.shouldScrollBottom =
      (window.innerHeight + window.scrollY) >= document.body.offsetHeight;
  },

  componentDidUpdate: function() {
    if (this.shouldScrollBottom) {
      this.scrollToBottom();
    }
  },

  scrollToBottom: function() {
    // http://blog.vjeux.com/2013/javascript/scroll-position-with-react.html
    // is a nice link to look at if you're modifying/debugging this
    window.scrollTo(0, document.body.scrollHeight);
  },

  pollForUpdates: function() {
    var latestData = this.props.initialLog.getReturnedData();
    if (this.state.newLogs.length > 0) {
      latestData = _.last(this.state.newLogs);
    }

    // the logic to decide whether to poll for updates happens here at the
    // beginning of the function - rather than the alternative of only calling
    // pollForUpdates when we know we want to poll.
    var should_poll = (
      // always poll if the log isn't finished
      latestData.source.step.status.id !== 'finished' ||
      // even if we are finished, keep polling until the api returns 0 chunks
      latestData.chunks.length > 0
    );

    if (!should_poll) {
      return;
    }

    var elem = this;
    var handle_response = function(response, was_success) {
      if (!was_success) {
        elem.setState({ updateError: response });
        return;
      }

      elem.setState((prev_state, current_props) => {
        return {
          newLogs: prev_state.newLogs.concat([JSON.parse(response.responseText)])
        }
      });

      elem.refreshTimer = window.setTimeout(_ => {
        if (!elem.isMounted()) {
          return;
        }
        elem.pollForUpdates();
      }, POLL_INTERVAL);
    }

    api.make_api_ajax_get(
      logging_endpoint(
        this.props.jobID,
        this.props.logsourceID,
        latestData.nextOffset),
      handle_response,
      handle_response);
  }
});

export default LogPage;
