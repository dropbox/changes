define([
  'jquery',
  'bootstrap/tooltip',
  'typeahead',
  'bloodhound'
], function(jQuery, tooltip, typeahead) {
  'use strict';

  // XXX(dcramer): not entirely sure why we have to do this
  jQuery.fn.tooltip = tooltip;
  jQuery.fn.typeahead = typeahead;
});
