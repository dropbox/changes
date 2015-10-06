import React, { PropTypes } from 'react';

import APINotLoaded from 'es6!display/not_loaded';
import ChangesUI from 'es6!display/changes/ui';

import * as api from 'es6!server/api';

import custom_content_hook from 'es6!utils/custom_content';

/*
 * Shows artifacts for a jobstep
 */
export var JobstepDetails = React.createClass({
  propTypes: {
    jobstepID: PropTypes.string,
  },

  getInitialState: function() {
    return {};
  },

  componentDidMount: function() {
    api.fetch(this, {
      artifacts: `/api/0/jobsteps/${this.props.jobstepID}/artifacts/`
    });
  },

  render: function() {
    var { jobstepID, className, ...props} = this.props;

    if (!api.isLoaded(this.state.artifacts)) {
      return <APINotLoaded calls={this.state.artifacts} />;
    }
    var artifacts = this.state.artifacts.getReturnedData();

    className = (className || "") + " jobstepDetails";

    return <div {...props} className={className}>
      {this.renderArtifacts(artifacts)}
    </div>;
  },

  renderArtifacts(artifacts) {
    var markup = [];
    if (artifacts.length > 0) {
      markup.push(<div className="lb marginTopM">Artifacts</div>);
      _.each(artifacts, a => {
        markup.push(
          <div> <a className="external" target="_blank" href={a.url}>
            {a.name}
          </a> </div>
        );
      });
    }

    return markup;
  }
});
