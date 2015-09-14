import React, { PropTypes } from 'react';

import * as utils from 'es6!utils/utils';

var cx = React.addons.classSet;

/*
 * Renders links to various pages. Usually returns anchor tags, but functions
 * ending in Href just return the URI (in case you need to customize.)
 */
var ChangesLinks = {

  author: function(author, subtle = false) {
    if (!author) {
      return 'unknown';
    }
    var classes = subtle ? "subtle" : "";
    var author_href = `/v2/author/${author.email}`;
    return <a href={author_href} className={classes}>
      {utils.email_head(author.email)}
    </a>;
  },

  project: function(project) {
    var href = ChangesLinks.projectHref(project);
    return <a href={href}>{project.name}</a>;
  },

  projectHref: function(project, tab = null) {
    var href = `/v2/project/${project.slug}/`;
    if (tab) {
      href += "#" + tab;
    }
    return href;
  },

  // renders the permalink url for an arbitrary build
  buildHref: function(build) {
    // three possibilities: this is a plain commit build, this is a diff build
    // from phabricator, or this is a build on an arbitrary code patch (e.g.
    // from arc test)

    if (!build.source.patch) {
      return URI(`/v2/commit/${build.source.id}/`)
        .search({ buildID: build.id })
        .toString();
    } else if (build.source.patch && build.source.data['phabricator.revisionID']) {
      return URI(`/v2/diff/D${build.source.data['phabricator.revisionID']}`)
        .search({ buildID: build.id })
        .toString();
    } else {
      return URI(`/v2/single_build/${build.id}/`);
    }
  },

  // as above, but for the case where we have many builds pointing to the same
  // target
  buildsHref: function(builds) {
    var build = builds[0];

    if (!build.source.patch) {
      return URI(`/v2/commit/${build.source.id}/`).toString();
    } else if (build.source.patch && build.source.data['phabricator.revisionID']) {
      return URI(`/v2/diff/D${build.source.data['phabricator.revisionID']}`).toString();
    } else {
      return URI(`/v2/single_build/${build.id}/`);
    }
  },
};

export default ChangesLinks;
