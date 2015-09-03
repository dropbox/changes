import React, { PropTypes } from 'react';

// TODO: trash me
var ErrorPage = React.createClass({
  render: function() {
    return <div>
      There was an error loading your page. Either this is a 404 or
      the URL didn{"'"}t have the info we needed
    </div>;
  }
});

export default ErrorPage;
