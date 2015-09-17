import React, { PropTypes } from 'react';

import Examples from 'es6!display/examples';
import { ChangesPage } from 'es6!display/page_chrome';

/* 
 * Renders example uses of the reusable display tags in display/
 */
var DisplayExamplesPage = React.createClass({

  getInitialTitle: function() {
    return "Examples";
  },

  render: function() {
    var removeHref = URI(window.location.href)
      .addQuery('disable_custom', 1)
      .toString();

    var removeLink = <a href={removeHref}>
      Render without any custom JS/CSS
    </a>;

    return <ChangesPage>
      <div className="marginBottomM">
        {removeLink}
      </div>
      {Examples.render()}
    </ChangesPage>;
  }
});

export default DisplayExamplesPage;
