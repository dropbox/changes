import React, { PropTypes } from 'react';

import ChangesLinks from 'es6!display/changes/links';
import SectionHeader from 'es6!display/section_header';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';
import { InfoList, InfoItem } from 'es6!display/info_list';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

/**
 * Views the file contents of a change. Useful for edge cases like arc test,
 * where there's no other way to see what code was run
 *
 * This page works for sources with a patch (diffs, arc test) and sources
 * without (plain commits)
 */
var CodePage = React.createClass({

  propTypes: {
    sourceID: PropTypes.string.isRequired,
  },

  getInitialState: function() {
    return {
      source: null,
    }
  },

  componentDidMount: function() {
    var sourceID = this.props.sourceID;

    api.fetch(this, {
      source: `/api/0/sources/${sourceID}`
    })
  },

  render: function() {
    if (!api.isLoaded(this.state.source)) {
      return <APINotLoadedPage calls={this.state.source} />;
    }

    var source = this.state.source.getReturnedData();
    console.log(source);
    utils.setPageTitle('Code');

    var message_lines = utils.split_lines(source.revision.message);
    var title = _.first(message_lines);
    var message_body = _.rest(message_lines).join("\n").trim();

    return <ChangesPage>
      <SectionHeader>{title}</SectionHeader>
      <pre style={{marginBottom: 15, marginTop: 5}}>
      {message_body}
      </pre>
      <InfoList className="marginBottomL">
        <InfoItem label="Internal Changes ID">
          {source.id}
        </InfoItem>
        <InfoItem label="Base Commit SHA">
          <a 
            className="external" 
            target="_blank" 
            href={ChangesLinks.phabCommitHref(source.revision)}>
            {source.revision.sha}
          </a>
        </InfoItem>
        <InfoItem label="Has Patch?">
          {source.patch ? 'Yes' : 'No'}
        </InfoItem>
      </InfoList>
      <pre className="defaultPre">
      {source.diff}
      </pre>
    </ChangesPage>;
  }
});

export default CodePage;
