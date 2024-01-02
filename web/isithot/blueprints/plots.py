from datetime import date
from datetime import timedelta
from typing import NamedTuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from flask_babel import _
from plotly.graph_objects import Figure
from scipy import stats


class PlotData(NamedTuple):
    """
    :param current_date: The date for which the data is compiled. This is
        usually today
    :param daily: A pandas dataframe containing all daily data that is
        available in the database
    :param now: The latest data from the station (high resolution raw data)
    :param toy_data: Data for the current time of year (toy). For this a week
        before ``current_data`` and a week after ``current_date`` is extracted
    :param trend_overall_data: (Yearly) data needed to calculate the overall
        trend since the start of the measurements
    :param trend_month_data: Data needed for calculating the trend for the
        current month
    :param calendar_data: Data needed to create a calendar plot for the current
        year
    :param trend_overall_slope: The slope of the line for the overall warming
        trend across all years and times of year
    :param trend_overall_intercept: The intercept of the line for the overall
        warming trend across all years and times of year
    :param trend_month_slope: The slope of the line for the current warming
        trend across all years for the current time of year :math:`\\pm` 7 days
    :param trend_month_intercept: The intercept of the line for the current
        warming trend across all years for the current time of year
        :math:`\\pm` 7 days
    :param current_avg: The current average of today calculated from averaging
        the minimum and maximum temperature
    :param current_avg_percentile: The percentile of ``current_avg``
    :param q5: the 5% percentile for this time of the year
    :param median: the median/50% percentile for this time of the year
    :param q95: the 95% percentile for this time of the year
    """
    current_date: date
    daily: pd.DataFrame
    now: pd.DataFrame
    toy_data: pd.DataFrame
    trend_overall_data: pd.DataFrame
    trend_month_data: pd.DataFrame
    calendar_data: pd.DataFrame
    trend_overall_slope: float
    trend_overall_intercept: float
    trend_month_slope: float
    trend_month_intercept: float
    current_avg: float
    current_avg_percentile: float
    q5: float
    median: float
    q95: float

    @property
    def yes_no(self) -> str:
        """returns a yes/no equivalent depending on the percentile"""
        if self.current_avg_percentile < 5:
            return _('Hell no!')
        elif 5 <= self.current_avg_percentile < 10:
            return _('No!')
        elif 10 <= self.current_avg_percentile < 40:
            return _('Nope')
        elif 40 <= self.current_avg_percentile < 50:
            return _('Not really')
        elif 50 <= self.current_avg_percentile < 60:
            return _('Yup')
        elif 60 <= self.current_avg_percentile < 90:
            return _('Yeah!')
        elif 90 <= self.current_avg_percentile < 95:
            return _('Hell yeah!')
        elif 95 <= self.current_avg_percentile <= 100:
            return _('Bloody hell yes!')
        else:
            return _('not sure, we have no data yet')

    @property
    def avg_compare(self) -> str:
        """returns a more comprehensive sentence of yes/no"""
        if self.current_avg_percentile < 5:
            return _("Are you kidding?! It's bloody cold")
        elif 5 <= self.current_avg_percentile < 10:
            return _("It's actually really cold")
        elif 10 <= self.current_avg_percentile < 40:
            return _("It's actually kinda cool")
        elif 40 <= self.current_avg_percentile < 50:
            return _("It's about average")
        elif 50 <= self.current_avg_percentile < 60:
            return _("It's warmer than average")
        elif 60 <= self.current_avg_percentile < 90:
            return _("It's quite %(hot_warm)s!", hot_warm=self.hot_warm)
        elif 90 <= self.current_avg_percentile < 95:
            return _("It's really %(hot_warm)s!", hot_warm=self.hot_warm)
        elif 95 <= self.current_avg_percentile <= 100:
            return _("It's bloody %(hot_warm)s!", hot_warm=self.hot_warm)
        else:
            return _('could be hotter, could be cooler')

    @property
    def hot_warm(self) -> str:
        if self.current_avg > 15:
            return _('hot')
        else:
            return _('warm')


def distrib_fig(fig_data: PlotData) -> Figure:
    """
    Creates a figures representing the distribution with 5% and 95% percentile
    and the trends for the time of year and the overall warming trend.

    :param fig_data: a :func:`PlotData` object containing all data necessary
        for creating the plot

    :returns: a :func:`Figure` object that can be used as a ``json`` on the
        page, defining the plot including all data
    """
    fig = go.Figure()

    # the dots representing the daily mean temperature
    fig.add_trace(
        go.Scatter(
            x=fig_data.toy_data.index,
            y=fig_data.toy_data['temp_mean_mannheim'],
            mode='markers',
            name=_('Daily Average Temperature'),
            marker={'size': 5, 'color': 'rgba(0, 0, 0, 0.2)'},
            showlegend=False,
            hovertemplate='<b>%{x|%Y-%m-%d}</b>: %{y:.1f} °C',
        ),
    ).update_layout(
        modebar={
            'bgcolor': 'rgba(0,0,0,0)',
            'color': 'rgba(0,0,0,1)',
            'activecolor': 'rgba(0,0,0,0.5)',
        },
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        yaxis_title=_('Daily Average Temperature (°C)'),
        template='simple_white',
        margin={'l': 0, 'r': 0, 't': 0, 'b': 0},
        yaxis={
            'fixedrange': True,
            'nticks': 10,
        },
        xaxis={
            'fixedrange': True,
            'nticks': 20,
        },
    )
    # the horizontal line indicating the 5% percentile
    fig.add_trace(
        go.Scatter(
            x=[
                (fig_data.toy_data.index.min() - timedelta(days=365)),
                (fig_data.toy_data.index.max() + timedelta(days=365*2)),
            ],
            y=[fig_data.q5, fig_data.q5],
            mode='lines+text',
            text=[_('<b>5th percentile: %(q5).1f °C</b>', q5=fig_data.q5)],
            textposition='top right',
            textfont_size=14,
            showlegend=False,
            line={'color': 'black', 'dash': 'dash', 'width': 3},
            hoverinfo='none',
        ),
    )
    # the horizontal line indicating the 95% percentile
    fig.add_trace(
        go.Scatter(
            x=[
                (fig_data.toy_data.index.min() - timedelta(days=365)),
                (fig_data.toy_data.index.max() + timedelta(days=365*2)),
            ],
            y=[fig_data.q95, fig_data.q95],
            mode='lines+text',
            showlegend=False,
            text=[_('<b>95th percentile: %(q95).1f °C</b>', q95=fig_data.q95)],
            textposition='top right',
            textfont_size=14,
            line={'color': 'black', 'dash': 'dash', 'width': 3},
            hoverinfo='none',
        ),
    )
    # the trend line for this time of the year
    fig.add_trace(
        go.Scatter(
            x=[
                fig_data.toy_data.index.min(),
                (fig_data.toy_data.index.max() + timedelta(days=365*2)),
            ],
            y=[
                fig_data.trend_month_intercept,
                fig_data.trend_month_intercept +
                len(fig_data.trend_month_data) * fig_data.trend_month_slope,
            ],
            mode='lines+text',
            showlegend=False,
            text=[
                _(
                    '<b>Trend for this time of year: '
                    '%(century_trend).1f K/century</b>',
                    century_trend=fig_data.trend_month_slope * 100,
                ),
            ],
            textposition='bottom right',
            textfont_size=14,
            line={'color': 'red', 'width': 3},
            hoverinfo='none',
        ),
    )
    # the overall trend line across all data
    fig.add_trace(
        go.Scatter(
            x=[
                (fig_data.toy_data.index.max() + timedelta(days=365*2)),
                fig_data.toy_data.index.min(),
            ],
            y=[
                fig_data.trend_month_intercept +
                len(fig_data.trend_overall_data) *
                fig_data.trend_overall_slope,
                fig_data.trend_month_intercept,
            ],
            mode='lines+text',
            showlegend=False,
            text=[
                _(
                    '<b>Overall Trend: %(century_trend).1f '
                    'K/century</b>',
                    century_trend=fig_data.trend_overall_slope * 100,
                ),
            ],
            textposition='top left',
            textfont_size=14,
            line={'color': 'red', 'width': 2, 'dash': 'dash'},
            hoverinfo='none',
        ),
    )
    # the red marker showing today's value
    fig.add_trace(
        go.Scatter(
            x=[fig_data.current_date],
            y=[fig_data.current_avg],
            mode='markers+text',
            marker={
                'size': 12, 'color': 'red', 'line': {
                    'color': 'rgba(255, 0, 0, 0.5)', 'width': 2,
                },
            },
            text=[
                _(
                    '<b>Today: %(cur_avg).1f °C</b>',
                    cur_avg=fig_data.current_avg,
                ),
            ],
            textfont_size=14,
            textposition='top left',
            showlegend=False,
            hoverinfo='none',
        ),
    )
    return fig


def hist_fig(fig_data: PlotData) -> Figure:
    """
    Creates a figures representing a histogram or more specifically a kernel
    density estimate. This includes lines for the 5% percentile and 95%
    percentile as well as the median. A red line for today's value is added.

    :param fig_data: a :func:`PlotData` object containing all data necessary
        for creating the plot

    :returns: a :func:`Figure` object that can be used as a ``json`` on the
        page, defining the plot including all data
    """
    # calculate the kernel density estimation curve
    kde = stats.gaussian_kde(fig_data.toy_data['temp_mean_mannheim'].dropna())

    # check the spacing with today's value. If we have a record, the plot may
    # be cut off - adjust this!
    kde_min = fig_data.toy_data['temp_mean_mannheim'].min()
    kde_max = fig_data.toy_data['temp_mean_mannheim'].max()
    # this ensures that today does not lay outside of the kde curve
    if fig_data.current_avg < kde_min:
        kde_min = fig_data.current_avg
    elif fig_data.current_avg > kde_max:
        kde_max = fig_data.current_avg

    x_vals = np.linspace(kde_min - 1, kde_max + 1, 200)
    y_vals = kde.evaluate(x_vals)

    fig = go.Figure()

    # Create line plot for KDE curve
    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='lines',
            line={'color': 'grey'},
            fill='tozeroy',
            showlegend=False,
            hoverinfo='none',
        ),
    )
    # the vertical line for the 5% percentile
    fig.add_trace(
        go.Scatter(
            x=[fig_data.q5, fig_data.q5],
            y=[max(y_vals), 0],
            mode='lines',
            showlegend=False,
            line={'color': 'black', 'dash': 'dash', 'width': 2},
            hoverinfo='none',
        ),
    )
    # the vertical line for the 95% percentile
    fig.add_trace(
        go.Scatter(
            x=[fig_data.q95, fig_data.q95],
            y=[max(y_vals), 0],
            mode='lines',
            showlegend=False,
            line={'color': 'black', 'dash': 'dash', 'width': 2},
            hoverinfo='none',
        ),
    )
    # the vertical line for the 50%/median percentile
    fig.add_trace(
        go.Scatter(
            x=[fig_data.median, fig_data.median],
            y=[max(y_vals), 0],
            mode='lines',
            showlegend=False,
            line={'color': 'black', 'dash': 'dash', 'width': 2},
            hoverinfo='none',
        ),
    )
    # # the vertical red line for today's temperature
    fig.add_trace(
        go.Scatter(
            x=[fig_data.current_avg, fig_data.current_avg],
            y=[max(y_vals), 0],
            mode='lines',
            showlegend=False,
            line={'color': 'red', 'width': 3},
            hoverinfo='none',
        ),
    )
    # making the plot transparent and adding the annotation for the lines
    # created above
    fig.update_layout(
        modebar={
            'bgcolor': 'rgba(0,0,0,0)',
            'color': 'rgba(0,0,0,1)',
            'activecolor': 'rgba(0,0,0,0.5)',
        },
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        xaxis_title=_('Daily Average Temperature (°C)'),
        template='simple_white',
        margin={'l': 0, 'r': 0, 't': 0, 'b': 0},
        yaxis={'visible': False},
        xaxis={
            'fixedrange': True,
            'nticks': 20,
        },
        annotations=[
            go.layout.Annotation(
                x=fig_data.q95,
                y=0,
                xref='x',
                yref='y',
                text=_('<b> 95th percentile: %(q95).1f °C</b>', q95=fig_data.q95),  # noqa: E501
                showarrow=False,
                yanchor='bottom',
                textangle=-90,
                xshift=-10,
            ),
            go.layout.Annotation(
                x=fig_data.q5,
                y=0,
                xref='x',
                yref='y',
                text=_('<b> 5th percentile: %(q5).1f °C</b>', q5=fig_data.q5),
                showarrow=False,
                yanchor='bottom',
                textangle=-90,
                xshift=-10,
            ),
            go.layout.Annotation(
                x=fig_data.median,
                y=0,
                xref='x',
                yref='y',
                text=_(
                    '<b> 50th percentile: %(med).1f °C</b>',
                    med=fig_data.median,
                ),
                showarrow=False,
                yanchor='bottom',
                textangle=-90,
                xshift=-10,
            ),
        ],
    )
    # there might be cases where we don't have data for today, so we cannot
    # annotate the red line (which is not drawn if it is nan)
    if not np.isnan(fig_data.current_avg):
        fig.add_annotation(
            go.layout.Annotation(
                x=fig_data.current_avg,
                y=max(y_vals),
                xref='x',
                yref='y',
                text=_(
                    '<b>Today: %(cur_avg).1f °C</b>',
                    cur_avg=fig_data.current_avg,
                ),
                showarrow=False,
                yanchor='top',
                textangle=-90,
                xshift=-10,
            ),
        )
    return fig


@np.vectorize
def _format_labels(x: float) -> str:
    """
    Helper to remove ``nan`` values from the labels. If not done, ``nan``s are
    displayed as ``0`` in the calendar plot. Floats are converted to ints.

    :param x: a floating point number which may be ``nan``

    :returns: A string representation of a float/int with 0 decimals and
        ``nan`` represented as ``''`` (an empty string)
    """
    return f'{x:.0f}' if not np.isnan(x) else ''


def calendar_fig(calendar_data: pd.DataFrame) -> Figure:
    """
    Creates a figures representing a calendar plot of the current year
    indicating the percentile of each day as a color and a number.

    :param calendar_data: a :func:`pd.DataFrame` containing all data necessary
        for creating the plot

    :returns: a :func:`Figure` object that can be used as a ``json`` on the
        page, defining the plot including all data
    """
    text = _format_labels(calendar_data.values)
    fig = px.imshow(
        calendar_data,
        color_continuous_scale='RdBu_r',
        aspect='auto',
        zmax=100,
        zmin=0,
    )
    fig.update_traces(text=text, texttemplate='%{text}')
    fig.update_coloraxes(colorbar={'thickness': 12, 'xpad': 0})
    fig.update_layout(
        modebar={
            'bgcolor': 'rgba(0,0,0,0)',
            'color': 'rgba(0,0,0,1)',
            'activecolor': 'rgba(0,0,0,0.5)',
        },
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        margin={'l': 0, 'r': 0, 't': 0, 'b': 0},
        hovermode=False,
        template='simple_white',
        xaxis={
            'fixedrange': True,
            'tickmode': 'linear',
            'tick0': 0,
            'dtick': 1,
            'title': None,
        },
        yaxis={
            'fixedrange': True,
            'tickmode': 'linear',
            'tick0': 0,
            'dtick': 1,
            'title': None,
        },
    )
    return fig
