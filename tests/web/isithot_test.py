import io
import os
from datetime import date

import numpy as np
import pandas as pd
import pytest
from freezegun import freeze_time
from PIL import Image
from PIL import ImageChops
from plotly.graph_objects import Figure
from sqlalchemy import text

from web.isithot.blueprints.isithot import _prepare_data
from web.isithot.blueprints.isithot import PlotData
from web.isithot.blueprints.plots import calendar_fig
from web.isithot.blueprints.plots import distrib_fig
from web.isithot.blueprints.plots import hist_fig


@pytest.fixture
def plot_data():
    return PlotData(
        current_date=date(2023, 12, 9),
        daily=pd.DataFrame(),
        now=pd.DataFrame(),
        toy_data=pd.DataFrame(),
        trend_overall_data=pd.DataFrame(),
        trend_month_data=pd.DataFrame(),
        calendar_data=pd.DataFrame(),
        trend_overall_slope=0,
        trend_overall_intercept=0,
        trend_month_slope=0,
        trend_month_intercept=0,
        current_avg=0,
        current_avg_percentile=0,
        q5=0,
        median=0,
        q95=0,
    )


@pytest.mark.parametrize(
    ('perc_val', 'txt'),
    (
        (1, 'Hell no!'),
        (7, 'No!'),
        (15, 'Nope'),
        (45, 'Not really'),
        (55, 'Yup'),
        (70, 'Yeah!'),
        (91, 'Hell yeah!'),
        (96, 'Bloody hell yes!'),
        (np.nan, 'not sure, we have no data yet'),
    ),
)
def test_plot_data_yes_no(perc_val, txt, plot_data):
    plot_data = plot_data._replace(current_avg_percentile=perc_val)
    assert plot_data.yes_no == txt


@pytest.mark.parametrize(
    ('perc_val', 'txt'),
    (
        (1, "Are you kidding?! It's bloody cold"),
        (7, "It's actually really cold"),
        (15, "It's actually kinda cool"),
        (45, "It's about average"),
        (55, "It's warmer than average"),
        (70, "It's quite hot!"),
        (91, "It's really hot!"),
        (96, "It's bloody hot!"),
        (np.nan, 'could be hotter, could be warmer'),
    ),
)
def test_plot_data_avg_compare(perc_val, txt, plot_data):
    plot_data = plot_data._replace(current_avg_percentile=perc_val)
    assert plot_data.avg_compare == txt


def assert_plot_is_equal(
        fig: Figure,
        baseline: str,
        diff_th: float = 0.0,
) -> None:
    with io.BytesIO() as current_img_bytes:
        # make the background white so we can actually see something!
        fig.update_layout(
            plot_bgcolor='rgba(255, 255, 255, 255)',
            paper_bgcolor='rgba(255, 255, 255, 255)',
            font_family='DejaVu Sans',
        )
        fig.write_image(file=current_img_bytes, format='jpeg', scale=1)

        with (
                Image.open(baseline) as baseline_img,
                Image.open(current_img_bytes) as current_img,
        ):
            baseline_array = np.array(baseline_img)
            current_array = np.array(current_img)

    diff = baseline_array - current_array
    diff_sum = np.abs(diff).sum()
    diff_sum_normed = diff_sum / baseline_array.size
    # this is only executed when a test fails
    if diff_sum_normed > diff_th:  # pragma: no cover
        diff = ImageChops.difference(baseline_img, current_img)
        diff_binary = np.array(diff)
        diff_binary[diff_binary > 0] = 255
        yellow = Image.new('RGB', diff.size, ('yellow'))
        yellow_diff = ImageChops.multiply(yellow, Image.fromarray(diff_binary))
        result = ImageChops.blend(yellow_diff, current_img, 0.2)

        # save to a folder to have a look at the diff
        os.makedirs('.pytest-img-comp', exist_ok=True)
        name, _ = os.path.splitext(os.path.basename(baseline))
        baseline_img.save(
            os.path.join('.pytest-img-comp', f'{name}_baseline.jpeg'),
        )
        current_img.save(
            os.path.join('.pytest-img-comp', f'{name}_current_img.jpeg'),
        )
        diff_path = os.path.join('.pytest-img-comp', f'{name}_diff_img.jpeg')
        result.save(diff_path)
        raise AssertionError(
            f'{diff_sum_normed} > {diff_th}: images differ (see: {diff_path})',
        )


@pytest.fixture
def test_data_lmss(engine):
    df = pd.read_csv('testing/monthly_input_data/lmss_daily_long.csv')
    df.to_sql('lmss_daily', con=engine, if_exists='append', index=False)
    yield
    with engine.connect() as con:
        con.execute(text('DELETE FROM lmss_daily'))


@pytest.mark.usefixtures('test_data_lmss', 'raw_table_data')
def test_distrib_plot_lmss(isithot_client):
    with isithot_client.application.app_context():
        plot_data = _prepare_data(d=date(2021, 5, 14), station='LMSS')
    fig = distrib_fig(plot_data)
    assert_plot_is_equal(
        fig, baseline='testing/plot_baseline/distrib_fig.jpeg',
    )


@pytest.mark.usefixtures('test_data_lmss', 'raw_table_data')
def test_hist_plot_lmss(isithot_client):
    with isithot_client.application.app_context():
        plot_data = _prepare_data(d=date(2021, 5, 14), station='LMSS')
    fig = hist_fig(plot_data)
    assert_plot_is_equal(fig, baseline='testing/plot_baseline/hist_fig.jpeg')


@pytest.mark.usefixtures('test_data_lmss', 'clean_tables')
def test_hist_plot_lmss_today_value_is_record(isithot_client, engine):
    with engine.connect() as con:
        query = '''\
            INSERT INTO lmss_garden_raw(date, temp_min, temp_max)
            VALUES ('2021-05-14 18:00', 5, 45)
        '''
        con.execute(text(query))

    with isithot_client.application.app_context():
        plot_data = _prepare_data(d=date(2021, 5, 14), station='LMSS')
    fig = hist_fig(plot_data)
    assert_plot_is_equal(
        fig,
        baseline='testing/plot_baseline/hist_fig_max_record.jpeg',
    )


@pytest.mark.usefixtures('test_data_lmss')
def test_hist_plot_lmss_no_current_data(isithot_client):
    with isithot_client.application.app_context():
        plot_data = _prepare_data(d=date(2021, 5, 14), station='LMSS')
    fig = hist_fig(plot_data)
    assert_plot_is_equal(
        fig,
        baseline='testing/plot_baseline/hist_fig_no_current_data.jpeg',
    )


@pytest.mark.usefixtures('test_data_lmss', 'raw_table_data')
def test_calendar_plot_lmss(isithot_client):
    with isithot_client.application.app_context():
        plot_data = _prepare_data(d=date(2021, 5, 14), station='LMSS')
    fig = calendar_fig(plot_data)
    assert_plot_is_equal(
        fig, baseline='testing/plot_baseline/calendar_fig.jpeg',
    )


@pytest.mark.usefixtures('test_data_lmss')
def test_root_redirects_to_lmss(isithot_client):
    rv = isithot_client.get('/isithot', follow_redirects=True)
    assert rv.request.path == '/isithot/lmss'
    assert rv.status_code == 200


@pytest.mark.parametrize('station', ('unknown-station', 'rgs', 'RGS'))
def test_isithot_station_not_found(isithot_client, station):
    rv = isithot_client.get(f'/isithot/{station}', follow_redirects=True)
    assert rv.status_code == 404


@pytest.mark.usefixtures('test_data_lmss')
def test_isithot_no_current_data_plots_are_omitted(isithot_client):
    rv = isithot_client.get('/isithot/lmss', follow_redirects=True)
    assert rv.status_code == 200
    data = rv.data.decode()
    # check that text is correct
    assert 'not sure, we have no data yet' in data
    assert 'could be hotter, could be warmer' in data
    assert '...and the rest of the year' in data
    # must not be in there and omitted
    assert "Here's how today compares..." not in data


@freeze_time('2021-05-14 22:00')
@pytest.mark.usefixtures('test_data_lmss', 'raw_table_data')
def test_isithot_lmss(isithot_client):
    rv = isithot_client.get('/isithot/lmss', follow_redirects=True)
    assert rv.status_code == 200
    data = rv.data.decode()
    # check that the page contents are correct
    assert 'Hell no!' in data
    assert 'Are you kidding?! It&#39;s bloody cold' in data
    assert "Here's how today compares..." in data
    assert '...and the rest of the year' in data
    # check the dynamic text
    assert 'maximum temperature so far is 11.2 °C' in data
    assert 'the minimum overnight was 0.6 °C' in data
    assert 'The average of the two is 5.9 °C' in data
    assert (
        'which is hotter than 0&#37; '
        'of daily average temperatures at LMSS'
    ) in data
    assert 'over the period 1912 - 2021' in data


@freeze_time('2021-05-14 22:00')
@pytest.mark.usefixtures('test_data_lmss', 'raw_table_data')
def test_isithot_lmss_german_locale(isithot_client):
    rv = isithot_client.get(
        '/isithot/lmss',
        headers={'Accept-Language': 'de-DE,en-US;q=0.7,en;q=0.3'},
    )
    assert rv.status_code == 200
    data = rv.data.decode()
    # check that the page contents are correct
    assert 'Auf gar keinen Fall!' in data
    assert 'Machst du Witze?! Es ist verdammt kalt' in data
    assert 'Der heutige Tag im Vergleich...' in data
    assert '...und der Rest des Jahres' in data
    # check the dynamic text
    assert 'Die heutige Maximaltemperatur bis jetzt ist 11.2 °C' in data
    assert 'die Minimumtemperatur ist 0.6 °C' in data
    assert 'Der Durchschnitt beider ist 5.9 °C' in data
    assert (
        'was wärmer als 0&#37; der täglichen mittleren Temperaturen an der '
        'LMSS'
    ) in data
    assert 'und im Zeitraum von 1912 - 2021' in data


@freeze_time('2021-05-14 22:00')
@pytest.mark.usefixtures('test_data_lmss', 'raw_table_data')
def test_isithot_lmss_locale_is_not_cached(isithot_client):
    # german request
    rv = isithot_client.get(
        '/isithot/lmss',
        headers={'Accept-Language': 'de-DE,en-US;q=0.7,en;q=0.3'},
    )
    assert rv.status_code == 200
    data_de = rv.data.decode()
    assert 'Auf gar keinen Fall!' in data_de

    # english request (must not be cached! since locale is different)
    rv = isithot_client.get(
        '/isithot/lmss',
        headers={'Accept-Language': 'en-US,en-US;q=0.7,en;q=0.3'},
    )
    assert rv.status_code == 200
    data_en = rv.data.decode()
    assert 'Hell no!' in data_en
