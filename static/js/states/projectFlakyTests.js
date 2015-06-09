define([
    'app'
], function(app) {
    'use strict';

    var CHART_DATA_LIMIT = 50;
    var MINIMUM_PASSING_RUNS = 50;

    return {
        parent: 'project_details',
        url: 'flaky_tests/?date',
        templateUrl: 'partials/project-flaky-tests.html',
        controller: function($scope, $state, projectData, flakyTestsData) {
            var genChartData = function(data, isOverallGraph) {
                return {
                    data: data.map(function(day) {
                        var className = 'result-unknown';
                        if (isOverallGraph || day.test_existed) {
                            className = day.flaky_runs > 0 ? 'result-failed' : 'result-passed';
                        }

                        var value = day.flaky_runs;
                        if (isOverallGraph) {
                            if (day.passing_runs < MINIMUM_PASSING_RUNS) {
                                className = 'result-unknown';
                                value = 0;
                            } else {
                                value = 100 * day.flaky_runs / day.passing_runs;
                            }
                        }

                        return {
                            className: className,
                            value: value,
                            data: day
                        };
                    }),
                    options: {
                        limit: CHART_DATA_LIMIT,
                        linkFormatter: function(item) {
                            return $state.href('project_flaky_tests', {date: item.date});
                        },
                        tooltipFormatter: function(item) {
                            var ratio = 0, extra_msg = '';
                            if (item.passing_runs > 0) {
                                ratio = (100 * item.flaky_runs/item.passing_runs).toFixed(2);
                            }
                            if (isOverallGraph && item.passing_runs < MINIMUM_PASSING_RUNS) {
                                extra_msg = '<p>The ratio of flaky runs on this date is not' +
                                    ' plotted because its flaky tests had less than ' +
                                    MINIMUM_PASSING_RUNS + ' passing runs.</p>';
                            }
                            return '<h5>' + item.date + '</h5>' + extra_msg +
                                '<p>Flaky runs: ' + item.flaky_runs +
                                ' (' + ratio + '% of passing runs)<br />' +
                                'Double flakes: ' + item.double_reruns + '</p>';
                        }
                     }
                };
            };

            // We set isOverallGraph so genChartData can differentiate individual test
            // history graph from the overall graph
            $scope.chartData = genChartData(flakyTestsData.chartData, true);

            flakyTestsData.flakyTests.map(function(test) {
                test.chartData = genChartData(test.history, false);

                // We create an element and get its outerHTML to escape the output.
                var text = document.createTextNode(test.output);
                var pre = document.createElement('pre');
                pre.appendChild(text);
                test.tooltip = pre.outerHTML;
            });
            $scope.flakyTests = flakyTestsData.flakyTests;

            $scope.date = flakyTestsData.date;
        },
        resolve: {
            flakyTestsData: function($http, $stateParams, projectData) {
                var url = '/api/0/projects/' + projectData.id + '/flaky_tests/?date=' +
                    ($stateParams.date || '');
                return $http.get(url).then(function(response) {
                    return response.data;
                });
            }
        }
    };
});
