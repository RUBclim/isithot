from datetime import date

import pandas as pd
from flask import abort
from flask import Blueprint
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import url_for
from pandas.core.api import DataFrame as DataFrame

from web.dashboard.models import db
from web.isithot.blueprints.plots import ColumnMapping
from web.isithot.blueprints.plots import DataProvider
from web.isithot.cache import cache

isithot = Blueprint(
    name='isithot',
    import_name=__name__,
    url_prefix='/isithot',
)


class Lmss(DataProvider):
    @cache.cached(timeout=300, key_prefix='daily_data')
    def get_daily_data(self, d: date) -> DataFrame:
        """Get the daily data for the LMSS from the database

        :param d: the date for which to prepare data. This will usually be
            today
        """
        daily_query = '''\
            SELECT
                date::TIMESTAMP,
                temp_mean_mannheim,
                EXTRACT(DOY FROM date) AS doy
            FROM lmss_daily ORDER BY date
        '''
        return pd.read_sql(sql=daily_query, con=db.engine, index_col='date')

    @cache.cached(timeout=300, key_prefix='current_data')
    def get_current_data(self, d: date) -> DataFrame:
        """Get today's data for the LMSS from the database

        :param d: the date for which to prepare data. This will usually be
            today
        """
        now_query = '''\
            SELECT
                date, temp_max, temp_min
            FROM lmss_garden_raw
            WHERE date > %(date)s
            ORDER BY date
        '''
        return pd.read_sql(
            sql=now_query,
            con=db.engine,
            index_col='date',
            params={'date': d},
        )


class Rgs(DataProvider):  # pragma: no cover
    def get_daily_data(self, d: date) -> DataFrame:
        """Get the daily data for the RGS II from the database

        :param d: the date for which to prepare data. This will usually be
            today
        """
        daily_query = '''\
            SELECT
                date::TIMESTAMP,
                temp_mean_mannheim,
                EXTRACT(DOY FROM date) AS doy
            FROM rgs_daily ORDER BY date
        '''
        return pd.read_sql(sql=daily_query, con=db.engine, index_col='date')

    def get_current_data(self, d: date) -> DataFrame:
        """Get today's data for the RGS II from the database

        :param d: the date for which to prepare data. This will usually be
            today
        """
        now_query = '''\
            SELECT
                date, temp_max, temp_min
            FROM rgs_raw
            WHERE date > %(date)s
            ORDER BY date
        '''
        return pd.read_sql(
            sql=now_query,
            con=db.engine,
            index_col='date',
            params={'date': d},
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


@isithot.route('/')
def index() -> Response:
    """
    A simple route to have nicer link to share. Redirects to the ``lmss``
    """
    return redirect(url_for('isithot.plots', station='lmss'))


def _i18n_cache_key(**kwargs: str) -> str:
    """Custom function for generating a cache-key based on strings passed as
    keyword arguments

    :param kwargs: any number of keyword arguments that are strings
    """
    return f'{"".join(kwargs.values())}-{get_locale()}'


COL_MAPPING = ColumnMapping(
    datetime='date',
    temp_mean='temp_mean_mannheim',
    temp_max='temp_max',
    temp_min='temp_min',
    day_of_year='doy',
)

# TODO: this is i.e. a feature flag for the RGS
DATA_PROVIDERS: dict[str, DataProvider] = {
    'lmss': Lmss(col_mapping=COL_MAPPING, name='LMSS', id='lmss'),
    # 'rgs': Rgs(col_mapping=COL_MAPPING, name='RGS II', id='rgs'),
}


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
    if station not in DATA_PROVIDERS.keys():
        abort(404)

    provider = DATA_PROVIDERS[station]

    data = provider.prepare_data(d=date.today())
    distrib_graph = provider.distrib_fig(data)
    hist_graph = provider.hist_fig(data)
    calender_graph = provider.calendar_fig(data.calendar_data)
    # because we have `orjson` installed, plotly tries to use this. But our
    # tests fail because it cannot serialize freezegun's FakeDateTime we need
    # to fallback to the builtin json module
    # https://github.com/spulec/freezegun/issues/448
    return render_template(
        'index.html',
        distrib_graph=distrib_graph.to_json(engine='json'),
        hist_graph=hist_graph.to_json(engine='json'),
        calender_graph=calender_graph.to_json(engine='json'),
        station=provider,
        plot_data=data,
        data_providers=DATA_PROVIDERS,
    )


@isithot.route('/other-years/<station>/<int:year>')
# we can cache this indefinitely since it's totally static
@cache.cached()
def last_years_calendar(station: str, year: int) -> str:
    """
    Returns the calendar figure data as ``json`` for the specified year.

    This route is cached indefinitely and does not take the locale into
    account, since it's only static data.

    :param station: The station a plot is created for. Either ``lmss`` or
        ``rgs``
    :param year: The year a plot is created for. Must be greater than 2010 and
        less than or equal to the current year
    """
    if station not in DATA_PROVIDERS.keys():
        abort(404)
    if not (2010 <= year <= date.today().year):
        abort(400)

    provider = DATA_PROVIDERS[station]

    _, calendar_data = provider.prepare_daily_and_calendar_data(
        d=date(year, 1, 1),
    )
    fig = provider.calendar_fig(calendar_data)
    return Response(fig.to_json(engine='json'), mimetype='application/json')
