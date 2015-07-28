import React from 'react';

import colors from 'es6!utils/colors';
import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

/*
 * A bunch of useful functions to render things like SHAs, author names, etc.
 * Naming is `changes_utils.js` since most utils are usually specific to the
 * changes UI, as opposed to most other components in this dir which are generic
 * for almost any tool.
 */
var DisplayUtils = {
  
  // If I want to be able to customize these (e.g. add a css class), they
  // should be tags instead

  author_link: function(author) {
    if (!author) {
      return 'unknown';
    }
    var author_href = `/v2/author/${author.email}`;
    return <a href={author_href}>
      {utils.email_head(author.email)}
    </a>;
  },

  // takes a blob of text and wraps urls in anchor tags
  linkify_urls: function(string, link_class = '') {
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

export default DisplayUtils;
