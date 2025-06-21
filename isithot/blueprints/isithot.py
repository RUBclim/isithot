from datetime import date

from flask import abort
from flask import Blueprint
from flask import current_app
from flask import redirect
from flask import render_template
from flask import request
from flask import Response
from flask import url_for

from isithot import DataProvider
from isithot.cache import cache

isithot = Blueprint(name='isithot', import_name=__name__)


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
    """A simple route to have nicer link to share."""
    return redirect(
        url_for(
            'isithot.plots',
            station=list(current_app.config['DATA_PROVIDERS'].keys())[0],
        ),
    )


def _i18n_cache_key(**kwargs: str) -> str:
    """Custom function for generating a cache-key based on strings passed as
    keyword arguments

    :param kwargs: any number of keyword arguments that are strings
    """
    return f'{"".join(kwargs.values())}-{get_locale()}'


@isithot.route('/<station>')
@cache.cached(timeout=300, make_cache_key=_i18n_cache_key)
def plots(station: str) -> str:
    """
    Renders the isithot page with all plots.

    This route is cached since compiling the data and generating the plots is
    quite expensive. The cache expires after 5 minutes hence it is still
    almost live data.

    :param station: The station a plot is created for.
    """
    if station not in current_app.config['DATA_PROVIDERS'].keys():
        abort(404)

    provider: DataProvider = current_app.config['DATA_PROVIDERS'][station]

    data = provider.prepare_data(d=date.today())
    distrib_graph = provider.distrib_fig(data)
    hist_graph = provider.hist_fig(data)
    calender_graph = provider.calendar_fig(data.calendar_data)
    return render_template(
        'index.html',
        distrib_graph=distrib_graph.to_json(engine='json'),
        hist_graph=hist_graph.to_json(engine='json'),
        calender_graph=calender_graph.to_json(engine='json'),
        station=provider,
        plot_data=data,
        data_providers=current_app.config['DATA_PROVIDERS'],
    )


@isithot.route('/other-years/<station>/<int:year>')
# we can cache this indefinitely since it's totally static
@cache.cached()
def last_years_calendar(station: str, year: int) -> str:
    """
    Returns the calendar figure data as ``json`` for the specified year.

    This route is cached indefinitely and does not take the locale into
    account, since it's only static data.

    :param station: The station a plot is created for.
    :param year: The year a plot is created for.
    """
    if station not in current_app.config['DATA_PROVIDERS'].keys():
        abort(404)

    provider: DataProvider = current_app.config['DATA_PROVIDERS'][station]

    if not (provider.min_year <= year <= date.today().year):
        abort(400)

    _, calendar_data = provider.prepare_daily_and_calendar_data(
        d=date(year, 1, 1),
    )
    fig = provider.calendar_fig(calendar_data)
    return Response(fig.to_json(engine='json'), mimetype='application/json')
