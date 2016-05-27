import React, { PropTypes } from 'react';
import moment from 'moment';

import classNames from 'classnames';

import SectionHeader from 'es6!display/section_header';
import { ChangesPage, APINotLoadedPage } from 'es6!display/page_chrome';

import { Grid, GridRow } from 'es6!display/grid';

import * as api from 'es6!server/api';

import * as utils from 'es6!utils/utils';

/**
 * Page with information on current active jobsteps.
 */
var JobstepSummaryPage = React.createClass({

  getInitialState() {
    return {
      jobstepAggregate: null,
    }
  },

  componentDidMount() {
    api.fetch(this, {
      jobstepAggregate: `/api/0/jobsteps/aggregate_by_status/`
    })
  },

  render() {
    if (!api.allLoaded([this.state.jobstepAggregate])) {
      return <APINotLoadedPage
        calls={[this.state.jobstepAggregate]}
      />;
    }

    utils.setPageTitle(`Active Jobsteps`);

    let data = this.state.jobstepAggregate.getReturnedData().jobsteps;
    return <ChangesPage>
      <SectionHeader>Active Jobsteps</SectionHeader>
      <GroupedJobstepSummary
            title="Global"
            data={data.global} />
      <GroupedJobstepSummary
        title="By Cluster"
        grouping="Cluster"
        data={data.by_cluster} />
      <GroupedJobstepSummary
        title="By Project"
        grouping="Project"
        data={data.by_project} />
    </ChangesPage>;
  }
});

var Age = React.createClass({
    propTypes: {
        created: PropTypes.string,
    },

    render() {
        let age = moment.utc(this.props.created).fromNow(true);
        return <span title={this.props.created}>{age} ago</span>;
    }
});

var SortHeader = React.createClass({
    propTypes: {
        parentElem: PropTypes.object.isRequired,
        label: PropTypes.string.isRequired,
        tag: PropTypes.string,
        sort: PropTypes.string.isRequired,
        reverse: PropTypes.bool.isRequired,
    },

    setSort(tag, rev) {
        this.props.parentElem.setSort(tag, rev);
    },

    render() {
        if (!this.props.tag) {
            return <div>{this.props.label}</div>;
        }
        let current = this.props.tag == this.props.sort;
        let dirarrow = null;
        if (current) {
            if (this.props.reverse) {
                dirarrow = <span> &#9650;</span>;
            } else {
                dirarrow = <span> &#9660;</span>;
            }
        }
        return <div className={classNames({menuItem: true,
                                           selectedMenuItem: current})}
                    onClick={() => this.setSort(this.props.tag, !this.props.reverse)}
                    >{this.props.label}{dirarrow}</div>;

    },
});

var GroupedJobstepSummary = React.createClass({
    propTypes: {
        title: PropTypes.string,
        grouping: PropTypes.string,
        data: PropTypes.object.isRequired,
    },

    getInitialState() {
        return {
            sort: 'group',
            reverse: false,
        }
    },

    setSort(tag, rev) {
        this.setState({sort: tag, reverse: rev});
    },

    render() {
        let rowify = (m) => {
            return _.map(m, (val, key) => {
                return [key, val[0], <JobstepInfo jobstepID={val[2]} />, <Age created={val[1]} />];
            });
        };

        let grouped = g => {
            let groups = _.map(_.keys(g).sort(), key => {
                let rows = rowify(g[key]);
                return _.map(rows, r => [key].concat(r) )
            });
            let result = [];
            _.forEach(groups, group => _.forEach(group, row => result.push(row)));
            return result;
        };

        // Column specification:
        //    label: The text describing the column.
        //    sortTag: Short url-safe string unique to the column, used to specify which column will be used to sort.
        //       Only for sortable columns.
        //    sortFn: Function used to extract a value useful for sorting from the column. Only for sortable columns.
        //    keyFn: Function for extracting a unique identifier for the row; only one column should set this.
        let columns = [
            {label: this.props.grouping, sortTag: 'group', sortFn: x => x},
            {label: 'Status', sortTag: 'status', sortFn: x => x},
            {label: 'Count', sortTag: 'count', sortFn: x => x},
            {label: 'Eldest', keyFn: x => x.props.jobstepID},
            {label: 'Eldest Age', sortTag: 'age', sortFn: x => x.props.created},
        ];

        const no_grouping = this.props.grouping === undefined;

        if (no_grouping) {
            columns.shift();
        }
        let headers = _.map(columns, col => {
            return <SortHeader parentElem={this} sort={this.state.sort} reverse={this.state.reverse}
                               label={col.label} tag={col.sortTag} />
        });
        let rows = [];
        if (no_grouping) {
            rows = rowify(this.props.data);
        } else {
            rows = grouped(this.props.data);
        }

        let sortFn = col => col[0];
        for (let i = 0; i < columns.length; i++) {
            let c = columns[i];
            if (c.sortTag == this.state.sort) {
                sortFn = col => c.sortFn(col[i]);
                break
            }
        }
        rows = _.sortBy(rows, sortFn);

        if (this.state.reverse) {
            rows.reverse();
        }
        if (!no_grouping) {
            let prev = undefined;
            for (let i = 0; i < rows.length; i++) {
                let row = rows[i];
                if (row[0] == prev) {
                    row[0] = '';
                } else {
                    prev = row[0];
                }
            }
        }
        let keyFn = null;
        for (let i = 0; i < columns.length; i++) {
            let c = columns[i];
            if (c.keyFn) {
                keyFn = r => c.keyFn(r[i]);
                break;
            }
        }
        if (!keyFn) {
            throw "Unable to find key function in column specifications";
        }
        let gridRows = _.map(rows, row => {
            return new GridRow(keyFn(row), row);
        });
        let cellClasses = _.times(columns.length, () => 'nowrap');
        return <div>
            <h3>{this.props.title}</h3>
            <Grid
                colnum={headers.length}
                headers={headers}
                cellClasses={cellClasses}
                data={gridRows}
            />
            </div>;
    }
});

var JobstepInfo = React.createClass({
  propTypes: {
    jobstepID: PropTypes.string.isRequired,
  },

  getInitialState() {
    return {};
  },

  componentDidMount() {
    api.fetch(this, {
      details: `/api/0/jobsteps/${this.props.jobstepID}/`
    });
  },

  render() {
    var { className, ...props} = this.props;

    if (!api.isLoaded(this.state.details)) {
      if (api.isError(this.state.details)) {
          return <div style={{color: 'red'}}>Failed.</div>;
      }
      return <div><i>Loading..</i></div>;
    }
    var details = this.state.details.getReturnedData();

    className = (className || "") + " jobstepDetails";

    return <div {...props} className={className}>
      <a href={`/find_build/${details.job.build.id}`}>{details.project.slug}</a>
    </div>;
  },

});

export default JobstepSummaryPage;
