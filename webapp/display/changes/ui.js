import React, { PropTypes } from 'react';
import moment from 'moment';

var cx = React.addons.classSet;

/*
 * Mostly things that seemed too small to be worth making into tags, e.g.
 * rendering a shorter name for a repo url.
 */
var ChangesUI = {

  // grabs the last path param or filename after : for a repo name
  getShortRepoName: function(repo_url) {
    return _.last(_.compact(repo_url.split(/:|\//)));
  },

  // projects whose last build was over a week old are considered stale
  projectIsStale: function(lastBuild) {
    var age = moment.utc().format('X') -
      moment.utc(lastBuild.dateCreated).format('X');

    return age > 60*60*24*7;
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
  }
};

export default ChangesUI;
