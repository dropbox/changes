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
    var author_href = `/author/${author.email}`;
    return <a href={author_href} className={classes}>
      {utils.email_head(author.email)}
    </a>;
  },

  project: function(project) {
    var href = ChangesLinks.projectHref(project);
    return <a href={href}>{project.name}</a>;
  },

  projectHref: function(project, tab = null) {
    var href = `/project/${project.slug}/`;
    if (tab) {
      href += "#" + tab;
    }
    return href;
  },

  // renders the permalink url for an arbitrary build
  buildHref: function(build) {
    if (!build) {
      console.error('tried to render a build link without a build!');
      return '';
    }

    // three possibilities: this is a plain commit build, this is a diff build
    // from phabricator, or this is a build on an arbitrary code patch (e.g.
    // from arc test)

    if (!build.source.patch) {
      return URI(`/commit_source/${build.source.id}/`)
        .search({ buildID: build.id })
        .toString();
    } else if (build.source.patch && build.source.data['phabricator.revisionID']) {
      return URI(`/diff/D${build.source.data['phabricator.revisionID']}`)
        .search({ buildID: build.id })
        .toString();
    } else {
      return URI(`/single_build/${build.id}/`);
    }
  },

  // as above, but for the case where we have many builds pointing to the same
  // target
  buildsHref: function(builds) {
    if (!builds || builds.length === 0) {
      console.error('tried to render a link for an empty list of builds!');
      return '';
    }

    var build = builds[0];

    if (!build.source) {
      // this can happen occasionally. I think its if you committed a diff
      // within the last few seconds...
      return '';
    } else if (!build.source.patch) {
      return URI(`/commit_source/${build.source.id}/`).toString();
    } else if (build.source.patch && build.source.data['phabricator.revisionID']) {
      return URI(`/diff/D${build.source.data['phabricator.revisionID']}`).toString();
    } else {
      return URI(`/single_build/${build.id}/`);
    }
  },

  phab: function(build) {
    if (_.contains(build.tags, 'arc test')) {
      return '';
    } else if (build.source.patch) {
      return <a
        className="external"
        href={build.source.data['phabricator.revisionURL']}
        target="_blank">
        {'D' + build.source.data['phabricator.revisionID']}
      </a>
    } else {
      return ChangesLinks.phabCommit(build.source.revision);
    }
  },

  phabCommit: function(revision) {
    var label = revision.sha.substr(0,7);
    return <a
      className="external"
      href={ChangesLinks.phabCommitHref(revision)}
      target="_blank">
      {label}
    </a>;
  },

  phabCommitHref: function(revision) {
    if (revision.external && revision.external.link) {
      return revision.external.link;
    }

    // if we don't have a link, let's just let the phabricator search engine
    // find the commit for us. It automatically redirects when only one commit
    // matches the sha
    var phab_host = window.changesGlobals['PHABRICATOR_HOST'];
    return URI(phab_host)
      .path('/search/')
      .addSearch('query', revision.sha)
      .toString();
  },

  snapshotImageHref: function(snapshotImage) {
     // We don't have a page for individual images, so we
     // link to the whole snapshot.
     return URI(`/v2/snapshot/${snapshotImage.snapshot.id}/`);
  }
};

export default ChangesLinks;
