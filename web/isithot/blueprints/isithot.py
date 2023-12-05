from datetime import date
from datetime import timedelta

import pandas as pd
from flask import abort
from flask import Blueprint
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import url_for
from scipy import stats
from sklearn.linear_model import LinearRegression

from web.dashboard.models import db
from web.isithot.blueprints.plots import calendar_fig
from web.isithot.blueprints.plots import distrib_fig
from web.isithot.blueprints.plots import hist_fig
from web.isithot.blueprints.plots import PlotData
from web.isithot.cache import cache

isithot = Blueprint(
    name='isithot',
    import_name=__name__,
    url_prefix='/isithot',
)


def get_locale() -> str | None:
    """
    utility for getting the lang from the ``Language-Accept`` header

    :returns: the language key - either ``de`` or ``en``
    """
    # the matching request.accept_languages.best_match algo is not great and
    # since we only have german and english avoid it
    if any(lang.startswith('de') for lang, _ in request.accept_languages):
        return 'de'
    else:
        return 'en'


def _prepare_data(d: date, station: str) -> PlotData:
    """
    The purpose of this function is to compile a
    :func:`web.isithot.blueprints.plots.PlotData()` object which is used for
    the creation of all plots.

    :param d: the date for which to prepare data. This will usually be today
    :param station: The station to prepare the data for. It can currently only
        be ``LMSS`` and ``RGS``

    :returns: the data needed for creating the plots and texts all contained in
        a :func:`web.isithot.blueprints.plots.PlotData()` object
    """
    if station == 'LMSS':
        daily_query = '''\
            SELECT date::TIMESTAMP, temp_mean_mannheim
            FROM lmss_daily ORDER BY date
        '''
    else:  # pragma: no cover
        daily_query = '''\
            SELECT date::TIMESTAMP, temp_mean_mannheim
            FROM rgs_daily ORDER BY date
        '''

    daily = pd.read_sql(sql=daily_query, con=db.engine, index_col='date')
    daily['doy'] = daily.index.dayofyear

    if station == 'LMSS':
        now_query = '''\
            SELECT
                date, temp_mean, temp_max, temp_min
            FROM lmss_garden_raw
            WHERE date > %(date)s
            ORDER BY date
        '''
    else:  # pragma: no cover
        now_query = '''\
            SELECT
                date, temp_mean, temp_max, temp_min
            FROM rgs_raw
            WHERE date > %(date)s
            ORDER BY date
        '''

    now = pd.read_sql(
        sql=now_query,
        con=db.engine,
        index_col='date',
        params={'date': d},
    )

    # warming trend for current time span of the year
    trend_overall_data = daily['temp_mean_mannheim'].resample(
        '1Y',
    ).mean().reset_index().dropna()
    reg = LinearRegression().fit(
        trend_overall_data.index.values.reshape(len(trend_overall_data), 1),
        trend_overall_data['temp_mean_mannheim'].values.reshape(
            len(trend_overall_data), 1,
        ),
    )
    trend_overall_intercept, = reg.intercept_
    trend_overall_slope, = reg.coef_[0]

    # extract data for distribution plots
    start = (d - timedelta(days=7))
    end = (d + timedelta(days=7))
    allowed_doy = pd.date_range(start=start, end=end, periods=14).day_of_year

    data = daily.loc[:f'{d.year}']  # type: ignore[misc]
    data = data[data['doy'].isin(allowed_doy)]

    # warming trend for current time span of the year
    trend_month_data = data['temp_mean_mannheim'].resample(
        '1Y',
    ).mean().reset_index().dropna()
    reg = LinearRegression().fit(
        trend_month_data.index.values.reshape(len(trend_month_data), 1),
        trend_month_data['temp_mean_mannheim'].values.reshape(
            len(trend_month_data), 1,
        ),
    )
    trend_month_intercept, = reg.intercept_
    trend_month_slope, = reg.coef_[0]

    # compile the current data
    today_data = now.loc[d:].agg(  # type: ignore[misc]
        {'temp_mean': 'mean', 'temp_min': 'min', 'temp_max': 'max'},
    )

    # TODO: what if it's the next day and not data is there (yet)
    current_avg = (today_data.temp_max + today_data.temp_min) / 2

    current_avg_perc = stats.percentileofscore(
        data['temp_mean_mannheim'], current_avg,
    )

    q5 = data['temp_mean_mannheim'].quantile(q=0.05)
    q95 = data['temp_mean_mannheim'].quantile(q=0.95)
    med = data['temp_mean_mannheim'].median()

    # prepare data for calendar plot
    def _calc_perc(x: pd.Series) -> pd.Series:
        start = (x.name - timedelta(days=7))
        end = (x.name + timedelta(days=7))
        allowed_doy = pd.date_range(
            start=start, end=end, periods=14,
        ).day_of_year

        data = daily[
            daily['doy'].isin(allowed_doy) &
            (daily.index.year < d.year)
        ]
        perc, = stats.percentileofscore(
            data['temp_mean_mannheim'],
            x,
            nan_policy='omit',
        )
        return perc

    calendar_data = daily.loc[f'{d.year}':]  # type: ignore[misc]
    # add the current day to the calendar plot
    calendar_data.loc[pd.Timestamp(d)] = [
        current_avg, d.timetuple().tm_yday,
    ]
    calendar_data.loc[:, 'perc'] = calendar_data[[
        'temp_mean_mannheim',
    ]].apply(_calc_perc, axis=1)
    # fill the year, so the plot always shows the entire year
    days = pd.date_range(
        start=date(d.year, 1, 1),
        end=date(d.year, 12, 31), freq='1D',
        name='date',
    )
    calendar_data = calendar_data.reindex(days)

    calendar_data.loc[:, 'day'] = calendar_data.index.day
    calendar_data.loc[:, 'month'] = calendar_data.index.month
    calendar_data.loc[:, 'month_name'] = calendar_data.index.strftime('%b')
    calendar_data = calendar_data.pivot(
        index=['month', 'month_name'],
        columns='day',
        values='perc',
    )
    calendar_data = calendar_data.reset_index('month').drop(['month'], axis=1)

    return PlotData(
        current_date=d,
        daily=daily,
        now=now,
        toy_data=data,
        trend_overall_data=trend_overall_data,
        trend_month_data=trend_month_data,
        calendar_data=calendar_data,
        trend_overall_slope=trend_overall_slope,
        trend_overall_intercept=trend_overall_intercept,
        trend_month_slope=trend_month_slope,
        trend_month_intercept=trend_month_intercept,
        current_avg=current_avg,
        current_avg_percentile=current_avg_perc,
        q5=q5,
        q95=q95,
        median=med,
    )


@isithot.route('/')
def index() -> Response:
    """
    A simple route to have nicer link to share. Redirects to the ``lmss``
    """
    return redirect(url_for('isithot.plots', station='lmss'))


def _i18n_cache_key(**kwargs: str) -> str:
    return f'{"".join(kwargs.values())}-{get_locale()}'


@isithot.route('/<station>')
@cache.cached(timeout=300, make_cache_key=_i18n_cache_key)
def plots(station: str) -> str:
    """
    Renders the isithot page with all plots. Currently only the ``LMSS`` is
    allowed since the data for the ``RGS`` is not fully available yet.

    This route is cached since compiling the data and generating the plots is
    quite expensive. The cache expires after 5 minutes hence it is still
    almost live data.

    :param station: The station a plot is created for. Either ``lmss`` or
        ``rgs``
    """
    station = station.upper()
    # TODO: this is i.e. a feature flag for the RGS
    if station not in ('LMSS',):
        abort(404)

    data = _prepare_data(d=date.today(), station=station)
    distrib_graph = distrib_fig(data)
    hist_graph = hist_fig(data)
    calender_graph = calendar_fig(data)
    return render_template(
        'index.html',
        distrib_graph=distrib_graph.to_json(),
        hist_graph=hist_graph.to_json(),
        calender_graph=calender_graph.to_json(),
        station=station,
        plot_data=data,
    )
