define([
  'jquery',
  'bootstrap/dropdown',
  'bootstrap/tooltip'
], function($, dropdown, tooltip) {
  'use strict';

  // XXX(dcramer): i have no idea
  $.fn.dropdown = dropdown;
  $.fn.tooltip = tooltip;
});
