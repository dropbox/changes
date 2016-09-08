import React from 'react';
import moment from 'moment';

import SimpleTooltip from 'es6!display/simple_tooltip';


// return the age of a build in seconds
function getBuildAge(lastBuild) {
  // NOTE: we use dateDecided because in the UI, we are only showing builds
  // that have finished
  var date = lastBuild.dateDecided ? lastBuild.dateDecided : lastBuild.dateModified;
  return moment.utc().format('X') - moment.utc(date).format('X');
}

/*
 * Mostly things that seemed too small to be worth making into tags, e.g.
 * rendering a shorter name for a repo url.
 */
var ChangesUI = {

  // grabs the last path param or filename after : for a repo name
  getShortRepoName: function(repo_url) {
    return _.last(_.compact(repo_url.split(/:|\//)));
  },

  getBuildAge: getBuildAge,

  // projects whose last build was over a week old are considered stale
  projectIsStale: function(lastBuild) {
    var age = getBuildAge(lastBuild)

    return age > 60*60*24*7;
  },

  // renders a lock icon with tooltip: you may need special permissions to see
  // this (I think not everyone can see Jenkins)
  restrictedIcon() {
    return <SimpleTooltip label="You may need special permissions to see this">
      <i className="fa fa-lock" style={{ opacity: "0.8" }}/>
    </SimpleTooltip>;
  },

  // takes a blob of text and wraps urls in anchor tags
  linkifyURLs: function(string, link_class = '') {
    var url_positions = [];
    URI.withinString(string, (url, start, end, source) => {
      url_positions.push([start, end]);
      return url;
    });

    var elements = [];

    // manual, sequential slicing
    var current_pos = 0;
    _.each(url_positions, pos => {
      var [start, end] = pos;
      elements.push(string.substring(current_pos, start));
      var uri = string.substring(start, end);
      elements.push(
        <a className={link_class} href={uri} target="_blank">
          {uri}
        </a>
      );
      current_pos = end;
    });
    elements.push(string.substring(current_pos));

    return elements;
  },

  /*
   * Allows us to have links that can dynamically change content using
   * javascript (tabs, paging buttons) but can still be opened in a new
   * window with ctrl/right click
   */
  leftClickOnly: function(wrapped_event_handler) {
    return function() {
      var args = Array.prototype.slice.call(arguments);
      var evt = args[0];
      if (evt.button !== 0) {
        // these return values might be ignored
        return true;
      }

      if (evt.altKey || evt.ctrlKey || evt.metaKey) {
        return true;
      }

      return wrapped_event_handler.apply(this, args);
    }
  }
};

export default ChangesUI;
