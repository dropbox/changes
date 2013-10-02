({
  appDir: "static",
  baseUrl: "js",
  dir: "dist/static/",
  paths: {
    'angular': 'vendor/angular/angular',
    'angularRoute': 'vendor/angular-route/angular-route',
    'angularAnimate': 'vendor/angular-animate/angular-animate',
    'bootstrap': 'vendor/bootstrap',
    'jquery': 'vendor/jquery/jquery',
    'moment': 'vendor/moment/moment'
  },
  shim: {
    'angular': {exports: 'angular'},
    'angularRoute': ['angular'],
    'angularAnimate': ['angular'],
    'jquery': {exports: 'jquery'},
    'bootstrap': {deps: ['jquery']},
  },
  modules: [
    {
      name: "main"
    }
  ]
})
