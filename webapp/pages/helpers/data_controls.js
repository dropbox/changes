import React from 'react';

import { TimeText } from 'es6!display/time';
import { StatusDot, status_dots, BuildWidget, get_build_cause } from 'es6!display/changes/builds';
import DisplayUtils from 'es6!display/changes/utils';
import { Grid } from 'es6!display/grid';
import { AjaxError, ProgrammingError } from 'es6!display/errors';
import APINotLoaded from 'es6!display/not_loaded';
import { RandomLoadingMessage } from 'es6!display/loading';
import ChangesPage from 'es6!display/page_chrome';
import { Menu1, Menu2, MenuUtils } from 'es6!display/menus';
import { Popover, OverlayTrigger } from 'react_bootstrap';

import * as api from 'es6!server/api';
import * as utils from 'es6!utils/utils';
import colors from 'es6!utils/colors';

var cx = React.addons.classSet;

/*
 * A data structure that handles pagination and table controls. Its designed
 * to be stored in a key in an element's state object, and exposes methods
 * that you can use to re-render the associated data table when any of
 * the variables in DataControls change.
 * 
 * Here's generally how you use it:
 * - Create it in componentWillMount inside your element's state object.
 *   Constructor params are the owner element and the state key being used,
 *   and the API url that returns different filtereds/sorteds views of the data
 * - Run initialize to get the initial data to populate your table. You should use
 *   getParamsFromWindowUrl() to get a set of parameters to send to the API 
 *   endpoint: the idea here is that whenever we make an API request, we update
 *   the window href with the api parameters we're using. That way, people can 
 *   share links with each other.
 * - Use an APINotLoaded component on controls.getDataToShow() if
 *   hasNotLoadedInitialData()
 * - Render your data using getDataToShow(). Give your grid opacity
 *   0.5 if isLoadingUpdatedData (and ideally disable modifying controls): this
 *   is a loading indicator. Render an error message if failedToLoadUpdatedData 
 *   (we tried and failed to load new data.)
 * - Add controls to let people change the data they're seeing. Controls state
 *   is encoded/decoded as the query params sent to the API: You can call
 *   getParamsToShow to get the query parameters used to render the 
 *   current data, then use that to render what state your controls are in.
 *   When someone changes your controls, call updateWithParams with the 
 *   query parameters you want to change.
 * - renderPaginationLinks renders pagination links.
 * - updateWindowUrl will update the current window href with the current
 *   controls state. Use this if, say, you have multiple tabs and you need to
 *   refresh the url every time you switch tabs.
 */
var DataControls = function(elem, elem_state_key, base_api_uri) {
  // TODO: we can't use classes right now because of the way ajax calls
  // directly update state (using the util func that sets a single key)
  return _.create(DataControlsPrototype, {
    // this object is hosted in a react elem's state variable. We need
    // this because we update ourself by calling 
    // setState(elem, { elemStateKey: ... })
    elem: elem,
    elemStateKey: elem_state_key,

    // we assume you're always hitting a single api endpoint. Worst case (e.g. 
    // for search support, we can make this a function on params.
    baseAPIUri: base_api_uri,

    // we make sure to only run kickoff once to fetch the initial data
    hasRunKickoff: false,

    // The data we show to the user
    currentParams: undefined,
    currentData: undefined,

    // Whenever we fetch new data from the api, we store the currently
    // displayed data here so that we can still render it while we wait
    loadingParams: undefined,
    loadingData: undefined
  });
}

/*
 * (static method) We usually mirror the API parameters in the page url. This
 * allows specific data views to be shared, if you use this function to
 * populate initialize(...)
 */
DataControls.getParamsFromWindowUrl = function() {
  return URI(window.location.href).search(true);
}

var DataControlsPrototype = {

  /*
   * Kicks off the initial data fetch. You can put this in componentDidMount,
   * or be lazier about when to fetch the data. Will only run at most once
   */
  initialize(initial_params) {
    if (this.hasRunKickoff) {
      return;
    }

    this.elem.setState(
      utils.update_state_dict(
        this.elemStateKey,
        {
          'hasRunKickoff': true,
          'currentParams': initial_params || {}
        }
      ),
      ___ => {
        api.fetchMap(
          this.elem,
          this.elemStateKey,
          { 
            'currentData': this._makeURI(initial_params) 
          }
        );
      }
    );
  },

  /*
   * This is the case where we have nothing to show to the user yet - we're still
   * waiting on the initial data fetch or there was an error with that fetch.
   */
  hasNotLoadedInitialData() {
    return this.loadingData === undefined && 
        !api.isLoaded(this.currentData);
  },

  /*
   * Are we in the process of loading newer data? (e.g. should we show
   * some kind of loading indicator?). This is the case where we already
   * have data and the user paginates / used a control to update the data.
   */
  isLoadingUpdatedData() {
    return !this.hasNotLoadedInitialData() &&
        !api.isLoaded(this.currentData) && 
        !api.isError(this.currentData);
  },

  /*
   * Did we try to fetch new data and fail at it?
   */
  failedToLoadUpdatedData() {
    return !this.hasNotLoadedInitialData() &&
      api.isError(this.currentData);
  },

  /*
   * ...if we did fail, returns the condition=error response
   */
  getDataForErrorMessage() {
    if (!this.failedToLoadUpdatedData) {
      throw 'Only call me when fetching new data failed!';
    }
    return this.currentData;
  },

  /*
   * Which data should we currently show to the user? Returns currentData
   * normally, and loadingData if we're waiting on a fetch for updatedData or
   * if that fetch for updatedData resulted in an error.
   */
  getDataToShow() {
    return this._getDataAndParamsToShow()['data'];
  },

  /*
   * ...and the query parameters associated with that data
   */
  getCurrentParams() {
    return _.clone(this._getDataAndParamsToShow()['params']);
  },

  /*
   * Call this when the user changes a control and you want to fetch new data
   * from the api. If the user clicks on a pagination link, we use paginate 
   * instead
   */
  updateWithParams(new_params, reset_page = false) {
    if (reset_page) {
      new_params['page'] = null;
      new_params['after'] = null;
      new_params['before'] = null;
    }
    var new_params = _.extend(this.getCurrentParams(), new_params);
    return this._fetchNewestData(new_params);
  },

  _paginate(page_params) {
    // when the user updates a control, we want to merge the updated param into
    // the params we're already sending the server. For pagination, though,
    // the server does this automatically for us.
    return this._fetchNewestData(page_params);
  },
  
  _fetchNewestData(params) {
    // optimistically change the window url to what we're about to load
    this.updateWindowUrl(params);

    // store the current data we're showing in loading before fetching new data
    this.elem.setState(utils.update_state_dict(
      this.elemStateKey, 
      {
        loadingParams: this.getCurrentParams(),
        loadingData: this.getDataToShow(),

        currentParams: params
      }
    ));
       
    api.fetchMap(
      this.elem,
      this.elemStateKey,
      { currentData: this._makeURI(params) }
    );
  },

  getPaginationLinks() {
    var hrefs = this.getDataToShow().getLinksFromHeader();
    var params = {
      previous: hrefs.previous && URI(hrefs.previous).search(true), 
      next: hrefs.next && URI(hrefs.next).search(true)
    };

    // the pagination api should return the same endpoint that we're already 
    // using, so we'll just grab the get params
    var on_click = params => this._paginate(params);

    var links = [];
    if (hrefs.previous) {
      links.push(
        <a 
          className="marginRightS"
          onClick={on_click.bind(this, params.previous)}>
          Previous
        </a>
      );
    }

    if (hrefs.next) {
      links.push(
        <a 
          className="marginRightS" 
          onClick={on_click.bind(this, params.next)}>
          Next 
        </a>
      );
    }

    return links;
  },

  // updates the window url with the parameters we're sending to the api.
  // This is almost always safe to call on re-render (w/o params)
  updateWindowUrl(params_to_use = null) {
    var params_to_use = params_to_use || this.getCurrentParams();
    params_to_use = _.pick(params_to_use, v => v !== null)
    var current_params = URI(window.location.href).search(true);

    if (!_.isEqual(params_to_use, current_params)) {
      window.history.replaceState(
        null,
        'changed data table',
        URI(window.location.href).query(params_to_use));
    }
  },

  // internal functions

  // combines a set of parameters and the baseAPIUri
  _makeURI(params) { 
    var params_to_set = _.pick(params, v => v !== null)
    return URI(this.baseAPIUri)
      .setSearch(params_to_set) // other params on baseAPIUri are unaffected
      .toString();
  },

  // Implementation for getDataToShow/getCurrentParams
  _getDataAndParamsToShow() {
    if (this.isLoadingUpdatedData() || this.failedToLoadUpdatedData()) {
      return { data: this.loadingData, params: this.loadingParams };
    }
    return { data: this.currentData, params: this.currentParams };
  }
};

export default DataControls;
