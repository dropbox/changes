define(['app'], function (app) {
  app.factory('flash', ['$rootScope', '$timeout', function($rootScope, $timeout){
    'use strict';

    var messages = [],
        reset;

    var cleanup = function() {
      $timeout.cancel(reset);
      reset = $timeout(function() {
        messages = [];
      });
    };

    var emit = function() {
      $rootScope.$emit('flash:message', messages, cleanup);
    };

    $rootScope.$on('$routeChangeSuccess', emit);

    var asMessage = function(level, text) {
      if (!text) {
        text = level;
        level = 'success';
      }
      return {
        level: level,
        text: text
      };
    };

    var asArrayOfMessages = function(level, text) {
      if (level instanceof Array) return level.map(function(message) {
        return message.text ? message : asMessage(message);
      });
      return text ? [{ level: level, text: text }] : [asMessage(level)];
    };

    return function(level, text) {
      emit(messages = asArrayOfMessages(level, text));
    };
  }]);
});
