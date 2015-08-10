import React from 'react';

import APINotLoaded from 'es6!display/not_loaded';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

var DetailsTab = React.createClass({

  propTypes: {
    // the API response from the fetch below
    details: React.PropTypes.object,
    // the project api response
    project: React.PropTypes.object,
  },

  componentDidMount: function() {
    var slug = this.props.project.getReturnedData().slug;
    api.fetch(this.props.pageElem, {
      details: `/api/0/projects/${slug}/plans/`
    });
  },

  render: function() {
    if (!api.isLoaded(this.props.details)) {
      return <APINotLoaded state={this.props.details} />;
    }

    var plans = this.props.details.getReturnedData();
    var project = this.props.project.getReturnedData();

    var markup = _.map(plans, p =>
      <div className="marginBottomL">
        <div style={{fontWeight: 900}}>{p.name}</div>
        <table className="invisibleTable">
        <tr>
          <td><b>Infrastructure:</b></td>
          <td>{!_.isEmpty(p.steps) && p.steps[0].name}</td>
        </tr> <tr>
          <td><b>Config:</b></td>
          <td> </td>
        </tr>
        </table>
        <pre className="yellowPre">
          {!_.isEmpty(p.steps) && p.steps[0].data}
        </pre>
      </div>
    );

    return <div>
      {this.renderHeader(project, plans)}
      {markup}
    </div>;
  },

  renderHeader: function(project, plans) {
    var builds_on_diffs = project.options["phabricator.diff-trigger"];
    var builds_on_commits = project.options["build.commit-trigger"];

    var triggers = 'Does not automatically run';
    if (builds_on_commits && builds_on_diffs) {
      triggers = 'Diffs and Commits';
    } else if (builds_on_diffs) {
      triggers = 'Only diffs';
    } else if (builds_on_commits) {
      triggers = 'Only commits';
    }

    var branches_option = project.options["build.branch-names"] || '*';
    var branches = branches_option === "*" ?
      'any' :
      branches_option.replace(/ /g, ", ");

    var whitelist_option = project.options["build.file-whitelist"].trim();
    var whitelist_paths = 'No path filter';
    if (whitelist_option) {
      whitelist_paths = _.map(utils.split_lines(whitelist_option), line => {
        <div>{line}</div>
      });
    }

    return <div className="marginBottomL">
      <span style={{fontWeight: 900}}>{project.name}</span>
      <table className="invisibleTable">
      <tr>
        <td><b>Repository:</b></td><td>{project.repository.url}</td>
      </tr> <tr>
        <td><b>Builds for:</b></td><td>{triggers}</td>
      </tr> <tr>
        <td><b>On branches:</b></td><td>{branches}</td>
      </tr> <tr>
        <td><b>Touching paths:</b></td><td>{whitelist_paths}</td>
      </tr> <tr>
        <td><b>Build plans</b></td><td>{plans.length}</td>
      </tr>
      </table>
    </div>;

    // TODO: how many tests? how many commits in the last week?
  }
});

export default DetailsTab;
