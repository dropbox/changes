'use strict';

var tests = [];
for (var file in window.__karma__.files) {
  if (window.__karma__.files.hasOwnProperty(file)) {
    if (/Spec\.js$/.test(file)) {
      tests.push(file.replace('/base/static/js', '../../'));
    }
  }
}

requirejs.config({
  // Karma serves files from '/base'
  baseUrl: '/base/static/js',

  paths: {
    'chai': '../../node_modules/chai/chai',
    'angularMocks': '../vendor/angular-mocks/angular-mocks',
    'sinon': '../../node_modules/sinon/lib/sinon'
  },

  shim: {
    'angularMocks': ['angular'],
    'sinon': {exports: 'sinon'}
  }
});

require(['main', 'chai', 'sinon'], function(_, chai, sinon){
  window.expect = chai.expect;
  window.sinon = sinon;

  require(['routes', 'angularMocks'], function(){
    require(tests, window.__karma__.start);
  });
});
