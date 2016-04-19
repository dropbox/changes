import React, { PropTypes } from 'react';
import { Modal } from 'react_bootstrap';

import ChangesLinks from 'es6!display/changes/links';
import SimpleTooltip from 'es6!display/simple_tooltip';
import { Button } from 'es6!display/button';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import { Error, AjaxError } from 'es6!display/errors';
import { Grid, GridRow } from 'es6!display/grid';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

// Disable log altogether lines >= 40K.
var MAX_LOG_LINES = 40960;

// how often to hit the api server for updates
var POLL_INTERVAL = 1000;

function is_eof(logApiResult) {
  if ("eof" in logApiResult && logApiResult.eof) {
    return true;
  }

  if ("source" in logApiResult && logApiResult.source.step.status.id === 'finished') {
    return true
  }

  return false;
}

function strip_ansi(s) {
    // Ideally we'd render the ANSI we can render, but this is better than showing it raw.
    // NB: The below regexp only tries to remove text styling, as that is most common and least
    // likely to cause confusion by being absent.
    return s.replace(/\x1B\[([0-9]{1,2}(;[0-9]{1,2})?)?m/g, '');
}

function logging_endpoint(url, offset = null) {
  var params = { limit: 0 };
  if (offset) {
    params.offset = offset;
  }

  return URI(url)
    .setSearch(params)
    .toString();
}

/**
 * Log that automatically tails and gets the latest updates. This page is just
 * a wrapper around LogComponent that fetches the initial data and renders the
 * page chrome
 */
var LogPage = React.createClass({

  propTypes: {
    jobID: PropTypes.string.isRequired,
    buildID: PropTypes.string.isRequired,
    logsourceID: PropTypes.string.isRequired,
  },

  getInitialState: function() {
    return {
      initialLog: null,
      build: null,

      showDebug: false,
    }
  },

  componentDidMount: function() {
    api.fetch(this, {
      build: `/api/0/builds/${this.props.buildID}`,
      job: `/api/0/jobs/${this.props.jobID}`
    });
  },

  getLogTailURL: function(job) {
    var lsID = this.props.logsourceID;
    return job.logs.filter(function(l) {
      return l.id == lsID;
    })[0].urls.filter(function(u) {
      return u.type == 'chunked';
    })[0].url;
  },

  render: function() {
    if (!api.allLoaded([this.state.job, this.state.build])) {
      return <APINotLoadedPage
        calls={[this.state.job, this.state.build]}
        fixed={true}
      />;
    }

    var jobName = this.state.job.getReturnedData().name;
    utils.setPageTitle(`Logs - ${jobName}`);

    var logURL = this.getLogTailURL(this.state.job.getReturnedData());

    return <ChangesPage fixed={true}>
      <LogComponent
        initialLogURL={logging_endpoint(logURL)}
        jobID={this.props.jobID}
        build={this.state.build}
        logsourceID={this.props.logsourceID}
      />
    </ChangesPage>;
  }
});

var LogComponent = React.createClass({

  propTypes: {
    initialLogURL: PropTypes.string.isRequired,
    build: PropTypes.object.isRequired,
  },

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

    api.fetch(this, {
      initialLog: this.props.initialLogURL,
    });
  },

  componentWillUnmount: function() {
    // clear the timer, if in use (e.g. the widget is expanded)
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }
  },

  render: function() {
    if (!api.isLoaded(this.state.initialLog)) {
      return <APINotLoadedPage calls={this.state.initialLog} />;
    }

    var initialLog = this.state.initialLog;

    var apiCallsToRender = [initialLog.getReturnedData()].concat(
      this.state.newLogs);

    var tooManyLines = false;
    var isFinished = false;
    var lines = [];
    _.each(apiCallsToRender, apiCall => {
      if (is_eof(apiCall)) {
        isFinished = true;
      }
      _.each(apiCall.chunks, chunk => {
        _.each(strip_ansi(chunk.text).split("\n"), line => {
          if (lines.length >= MAX_LOG_LINES) {
            tooManyLines = true;
            return;
          }
          lines.push(
            <div className="line">{line}</div>
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

  renderDebugContent() {
    var initialLog = this.state.initialLog;

    var allApiCalls = [initialLog.getReturnedData()].concat(
      this.state.newLogs);

    var data = [];

    var source = 0;
    var expectedOffset = 0;
    _.each(allApiCalls, call => {
      _.each(call.chunks, chunk => {
        var icon = chunk.offset === expectedOffset ?
          <SimpleTooltip label="This offset looks correct">
            <i className="marginLeftS fa fa-check green" />
          </SimpleTooltip> :
          <SimpleTooltip 
            label="This offset doesn't look right. Did we not render some log lines?">
            <i className="marginLeftS fa fa-times red" />
          </SimpleTooltip>;
        var offsetText = <span>{chunk.offset}{icon}</span>;
        var sourceText = source === 0 ? "initial" : "api call #" + source;
        data.push([offsetText, chunk.size, sourceText]);
        expectedOffset = chunk.offset + chunk.size;
      });
      data.push(GridRow.oneItem("End of call. Next Offset: " + call.nextOffset));
      expectedOffset = call.nextOffset;
      source += 1;
    });

    return <div>
      <div>Maximum line count: {MAX_LOG_LINES}</div>
      <div>Poll interval: {POLL_INTERVAL}</div>
      <Grid
        colnum={3}
        data={data}
        headers={['Offset', 'Chunk', 'Source']}
      />
      This debugging info may not help you diagnose cases where we prematurely
      stop fetching log lines before the log is complete.
    </div>
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
        {utils.truncate(build.name)}
      </div>;
    }

    var showDebug = __ => { this.setState({showDebug: true}); };
    var hideDebug = __ => { this.setState({showDebug: false}); };

    // this is rendered separately, and won't be picked up by the componentDidMount
    // of the general page when there is an admin message
    var messageNode = document.getElementsByClassName('persistentMessage')[0];
    var topMargin = messageNode ? messageNode.offsetHeight : 0;
    var style = {marginTop: topMargin + "px"};

    return <div className="logReturnLink" style={style}>
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
      <a className="logDebugLink" onClick={showDebug}>
        Debugging Info
      </a>
      <Modal animation={false} show={this.state.showDebug} onHide={hideDebug}>
        <Modal.Header closeButton>
          <Modal.Title>Debugging Info</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {this.renderDebugContent()}
        </Modal.Body>
        <Modal.Footer>
          <Button onClick={hideDebug}>Close</Button>
        </Modal.Footer>
      </Modal>
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
    var latestData = this.state.initialLog.getReturnedData();
    if (this.state.newLogs.length > 0) {
      latestData = _.last(this.state.newLogs);
    }

    // the logic to decide whether to poll for updates happens here at the
    // beginning of the function - rather than the alternative of only calling
    // pollForUpdates when we know we want to poll.
    var should_poll = (
      // always poll if the log isn't finished
      ! is_eof(latestData) ||
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
        this.props.initialLogURL,
        latestData.nextOffset),
      null,
      handle_response,
      handle_response);
  }
});

export default LogPage;
