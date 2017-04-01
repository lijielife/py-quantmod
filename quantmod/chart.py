"""Main Chart functionnality

Chart is a wrapper on top of DataFrame that
adds functionnality and allows for easy plotting.
Features include time series adjustement, volume adjustement, and
plotting of OHLCV data with over 100 technical indicators.

"""
from __future__ import absolute_import

import copy
import six
import datetime as dt
import pandas as pd
import plotly.plotly as py
import plotly.offline as pyo

from . import tools
from . import factory
from .valid import *
from .ta import *


class Chart(object):
    """Quantmod Chart based on Pandas DataFrame.

    Chart is a wrapper on top of DataFrame that
    adds functionnality and allows for easy plotting.
    Features include time series adjustement, volume adjustement, and
    plotting of OHLCV data with over 100 technical indicators.

    """
    def __init__(self, df, src=None,
                 ticker=None, start=None, end=None):
        """Quantmod Chart based on Pandas DataFrame.

        Chart is a wrapper on top of DataFrame that
        adds functionnality and allows for easy plotting.
        Features include time series adjustement, volume adjustement, and
        plotting of OHLCV data with over 100 technical indicators.

        Parameters
        ----------
            df : DataFrame
                Underlying DataFrame containing ticker data.
            src : string or dict
                If string, provenance of data (e.g. 'google', 'yahoo') to
                automatically map column names to OHLCV data.
                If dict, directly specifies how column names map to OHLCV data.
            ticker : string or False, default False
                Ticker associated with data. Used to plot titles.
                If False no ticker is specified.
            start : datetime, string or False, default df.index[0]
                Left boundary for date range, specified
                either as string or as a datetime object.
                If False no start is specified. Default set to first
                element of df.index.
            end : datetime, string or False, default df.index[-1]
                Right boundary for date range, specified
                either as string or as a datetime object.
                If False no start is specified. Default set to last
                element of df.index.
        """
        self.df = df

        # Test if src is string or dict, or get default vendor otherwise
        if src is not None:
            if isinstance(src, six.string_types):
                src = factory.get_source(src)
            elif isinstance(src, dict):
                pass
            else:
                raise TypeError("Invalid src '{0}'. "
                                "It should be string or dict."
                                .format(src))
        else:
            src = factory.get_source(tools.get_config_file()['source'])

        # Check if ticker is valid
        if ticker is not None:
            if ticker == False:
                pass
            elif isinstance(ticker, six.string_types):
                pass
            else:
                raise TypeError("Invalid ticker '{0}'. "
                                "It should be string or dict."
                                .format(ticker))
        else:
            ticker = False

        # Check if start is valid
        if start is not None:
            if start == False:
                pass
            elif isinstance(start, six.string_types):
                pass
            elif isinstance(start, dt.dateime):
                pass
            else:
                raise TypeError("Invalid start '{0}'. "
                                "It should be string or datetime."
                                .format(start))
        else:
            start = self.df.index[0]

        # Check if end is valid
        if end is not None:
            if end == False:
                pass
            elif isinstance(end, six.string_types):
                pass
            elif isinstance(end, dt.dateime):
                pass
            else:
                raise TypeError("Invalid end '{0}'. "
                                "It should be string or datetime."
                                .format(end))
        else:
            end = self.df.index[-1]

        self.ticker = ticker
        self.start = start
        self.end = end

        self.op = src['op']
        self.hi = src['hi']
        self.lo = src['lo']
        self.cl = src['cl']
        self.aop = src['aop'] # Not used currently
        self.ahi = src['ahi'] # Not used currently
        self.alo = src['alo'] # Not used currently
        self.acl = src['acl']
        self.vo = src['vo']
        self.di = src['di'] # Not used currently

        self.ind = pd.DataFrame([], index=self.df.index)
        self.pri = {}
        self.sec = {}

    def __repr__(self):
        """Return representation of Chart object."""
        return str(self.to_frame())

    def __len__(self):
        """Return length of Chart object."""
        return len(self.to_frame())

    @property
    def shape(self):
        """Return shape of Chart object."""
        return self.to_frame().shape

    @property
    def has_open(self):
        """Return True if Chart DataFrame has open, False otherwise."""
        if self.op in self.df.columns:
            return True
        else:
            return False

    @property
    def has_high(self):
        """Return True if Chart DataFrame has high, False otherwise."""
        if self.hi in self.df.columns:
            return True
        else:
            return False

    @property
    def has_low(self):
        """Return True if Chart DataFrame has low, False otherwise."""
        if self.lo in self.df.columns:
            return True
        else:
            return False

    @property
    def has_close(self):
        """Return True if Chart DataFrame has close, False otherwise."""
        if self.cl in self.df.columns:
            return True
        else:
            return False

    @property
    def has_adjusted_open(self):
        """Return True if Chart DataFrame has adjusted open, False otherwise."""
        if self.aop in self.df.columns:
            return True
        else:
            return False

    @property
    def has_adjusted_high(self):
        """Return True if Chart DataFrame has adjusted high, False otherwise."""
        if self.ahi in self.df.columns:
            return True
        else:
            return False

    @property
    def has_adjusted_low(self):
        """Return True if Chart DataFrame has adjusted low, False otherwise."""
        if self.alo in self.df.columns:
            return True
        else:
            return False

    @property
    def has_adjusted_close(self):
        """Return True if Chart DataFrame has adjusted close, False otherwise."""
        if self.acl in self.df.columns:
            return True
        else:
            return False

    @property
    def has_volume(self):
        """Return True if Chart DataFrame has volume, False otherwise."""
        if self.vo in self.df.columns:
            return True
        else:
            return False

    @property
    def has_dividend(self):
        """Return True if Chart DataFrame has dividend, False otherwise."""
        if self.di in self.df.columns:
            return True
        else:
            return False

    @property
    def has_OHLC(self):
        """Return True if Chart DataFrame has OHLC, False otherwise."""
        cols = {self.op, self.hi, self.lo, self.cl}
        arr = self.df.columns.isin(cols)
        return sum(arr) >= len(cols)

    @property
    def has_OHLCV(self):
        """Return True if Chart DataFrame has OHLCV, False otherwise."""
        cols = {self.op, self.hi, self.lo, self.cl, self.vo}
        arr = self.df.columns.isin(cols)
        return sum(arr) >= len(cols)

    def adjust(self, inplace=False):
        """Adjust OHLC data for splits, dividends, etc.

        Requires an adjusted close column to adjust the rest of the OHLC bars.

        Parameters
        ----------
            inplace : bool
                Modifies Chart inplace (returns None) if True, else
                returns modified Chart by default.

        """
        if not self.has_OHLC and self.has_adjusted_close:
            raise Exception("Insufficient data to adjust OHLC data.")

        ratio = (self.df[self.cl] / self.df[self.acl])

        if inplace:
            self.df[self.op] = self.df[self.op] / ratio
            self.df[self.hi] = self.df[self.hi] / ratio
            self.df[self.lo] = self.df[self.lo] / ratio
            self.df[self.cl] = self.df[self.cl] / ratio
        else:
            df2 = self.df.copy()
            df2[self.op] = self.df[self.op] / ratio
            df2[self.hi] = self.df[self.hi] / ratio
            df2[self.lo] = self.df[self.lo] / ratio
            df2[self.cl] = self.df[self.cl] / ratio
            return Chart(df2)

    def adjust_volume(self, inplace=False):
        """Adjust volume data for splits, dividends, etc.

        Requires a close and and adjusted close column to adjust volume.

        Parameters
        ----------
            inplace : bool, default False
                Modifies Chart inplace (returns None) if True, else
                returns modified Chart by default.

        """
        if not self.has_volume and self.has_close and self.has_adjusted_close:
            raise Exception("Insufficient data to adjust volume.")

        ratio = (self.df[self.cl] / self.df[self.acl])

        if inplace:
            self.df[self.vo] = self.df[self.vo] / ratio
        else:
            df2 = self.df.copy()
            df2[self.vo] = self.df[self.vo] / ratio
            return Chart(df2)

    def to_frame(self):
        """Return DataFrame representation of Chart, including all added
        technical indicators."""
        return self.df.join([self.ind])

    def to_figure(self, type=None, volume=None,
                  theme=None, layout=None,
                  title=None, subtitle=None, hovermode=None,
                  legend=None, annotations=None, shapes=None,
                  dimensions=None, width=None, height=None, margin=None,
                  **kwargs):
        """Return Plotly figure (dict) that is used to generate the stock chart.

        Parameters
        ----------
            type : {'ohlc', 'candlestick',
                    'line', 'line_thin', 'line_thick', 'line_dashed',
                    'line_dashed_thin', 'line_dashed_thick',
                    'area', 'area_dashed',
                    'area_dashed_thin', 'area_dashed_thick', 'area_threshold',
                    'scatter'}
                Determine the chart type of the main trace. For candlestick
                and OHLC bars Chart needs to have OHLC enabled.
            volume : bool
                Toggle the diplay of a volume subplot in chart.
            theme : string
                Quantmod theme.
            layout : dict or Layout
                Plotly layout dict or graph_objs.Layout object.
                Will override all other arguments if conflicting as
                user-inputted layout is updated last.
            title : string
                Chart title.
            subtitle : bool, default True
                Toggle the display of last price and/or volume in chart.
            hovermode : {'x', 'y', 'closest', False}
                Toggle how a tooltip appears on cursor hover.
            legend : dict, Legend or bool, default True
                True/False or Plotly legend dict / graph_objs.Legend object.
                If legend is bool, Quantmod will only toggle legend visibility.
            annotations : list or Annotations
                Plotly annotations list / graph.objs.Annotations object.
            shapes : list or Shapes
                Plotly shapes list or graph_objs.Shapes object.
            dimensions : tuple
                Dimensions 2-tuple in order (width, height).
                Disables autosize=True in plotly.
            width : int
                Width of chart.
                Disables autosize=True in plotly.
            height : int
                Height of chart.
                Disables autosize=True in plotly.
            margin : dict or tuple
                Plotly margin dict or 4-tuple in order (l, r, b, t) or
                5-tuple in order (l, r, b, t, margin). Tuple input added for
                Cufflinks compatibility.

        Examples
        --------
            ch = qm.Chart(df)
            ch.to_figure(type='ohlc', dimensions=(2560,1440))

            ch = qm.Chart(df)
            ch.add_BBANDS()
            ch.add_RSI(14)
            ch.to_figure(type='candlestick', title='EQUITY')

        """
        # Check for kwargs integrity
        for key in kwargs:
            if key not in VALID_FIGURE_KWARGS:
                raise Exception("Invalid keyword '{0}'.".format(key))

        # Kwargs renaming
        if 'kind' in kwargs:
            type = kwargs['kind']

        if 'showlegend' in kwargs:
            legend = kwargs['showlegend']

        if 'figsize' in kwargs: # Matplotlib
            figsize = kwargs['figsize']
            if isinstance(figsize, tuple):
                if len(figsize) == 2:
                    dimensions = tuple(80 * i for i in figsize) # 80x size
                else:
                    raise Exception("Invalid figsize '{0}'. "
                                    "It should be tuple of len 2."
                                    .format(figsize))
            else:
                raise TypeError("Invalid figsize '{0}'. "
                                "It should be tuple."
                                .format(figsize))

        # Default argument values
        if type is None:
            if self.has_OHLC:
                type = 'candlestick'
            elif self.has_close:
                type = 'line'
            else:
                raise Exception("Chart has neither OLHC nor close data.")

        if volume is None:
            if self.has_volume:
                volume = True
            else:
                volume = False

        if title is None:
            if self.ticker:
                title = ticker
            else:
                title = ''

        if subtitle is None:
            subtitle = True

        if legend is None:
            legend = True

        # Type checks for mandatorily used arguments
        if not isinstance(type, six.string_types):
            raise TypeError("Invalid type '{0}'. "
                            "It should be string."
                            .format(type))
            if type not in VALID_TRACES:
                raise Exception("Invalid keyword '{0}'. "
                                "It is not in VALID_TRACES."
                                .format(type))
            if type in OHLC_TRACES:
                if not self.has_OHLC:
                    raise Exception("Insufficient data for '{}'. "
                                    "Chart does not have OHLC data."
                                    .format(type))
            else:
                if not self.has_close:
                    raise Exception("Insufficient data for '{}'. "
                                    "Chart does not have close data."
                                    .format(type))

        if not isinstance(volume, bool):
            raise TypeError("Invalid volume'{0}'. "
                            "It should be bool."
                            .format(volume))

        if not isinstance(subtitle, bool):
            raise TypeError("Invalid subtitle'{0}'. "
                            "It should be bool."
                            .format(subtitle))

        # Get template and bind to colors, traces, additions and layotu
        template = factory.get_template(theme=theme, layout=layout,
                                      title=title,
                                      hovermode=hovermode, legend=legend,
                                      annotations=annotations, shapes=shapes,
                                      dimensions=dimensions,
                                      width=width, height=height,
                                      margin=margin)
        colors = template['colors']
        traces = template['traces']
        additions = template['additions']
        layout = template['layout']

        # Get data
        data = []

        # Plot main chart
        if type in OHLC_TRACES:
            trace = copy.deepcopy(traces[type])

            trace['x'] = self.df.index
            trace['open'] = self.df[self.op]
            trace['high'] = self.df[self.hi]
            trace['low'] = self.df[self.lo]
            trace['close'] = self.df[self.cl]
            trace['name'] = title
            trace['yaxis'] = 'y1'
            trace['showlegend'] = False

            # Colors
            if type == 'candlestick':
                trace['increasing']['fillcolor'] = colors['increasing']
                trace['increasing']['line']['color'] = colors['border']
                trace['decreasing']['fillcolor'] = colors['decreasing']
                trace['decreasing']['line']['color'] = colors['border']

            if type == 'ohlc':
                trace['increasing']['line']['color'] = colors['increasing']
                trace['decreasing']['line']['color'] = colors['decreasing']

            data.append(trace)

        elif 'line' in type:
            trace = copy.deepcopy(traces[type])

            trace['x'] = self.df.index
            trace['y'] = self.df[self.cl]
            trace['name'] = title
            trace['yaxis'] = 'y1'
            trace['showlegend'] = False

            # Colors
            trace['line']['color'] = colors['primary']

            data.append(trace)

        elif 'area' in type:
            trace = copy.deepcopy(traces[type])

            trace['x'] = self.df.index
            trace['y'] = self.df[self.cl]
            trace['name'] = title
            trace['yaxis'] = 'y1'
            trace['showlegend'] = False

            # Colors
            trace['line']['color'] = colors['primary']

            data.append(trace)

        elif 'scatter' in type:
            trace = copy.deepcopy(traces[type])

            trace['x'] = self.df.index
            trace['y'] = self.df[self.cl]
            trace['name'] = title
            trace['yaxis'] = 'y1'
            trace['showlegend'] = False

            # Colors
            trace['scatter']['color'] = colors['primary']

            data.append(trace)

        else:
            raise Exception("Cannot plot this chart type '{0}'.".format(type))

        # Plot primary indicators
        for name in self.pri:
            primary = self.pri[name]
            trace = copy.deepcopy(traces[primary['type']])

            trace['x'] = self.ind.index
            trace['y'] = self.ind[name]
            trace['name'] = name
            trace['yaxis'] = 'y1'

            # Colors
            trace['line']['color'] = colors[primary['color']]

            if 'area' in primary['type']:
                if 'fillcolor' in primary:
                    trace['fillcolor'] = colors[primary['fillcolor']]

            data.append(trace)

        # Plot volume
        if volume:
            trace = copy.deepcopy(traces['bar'])

            trace['x'] = self.df.index
            trace['y'] = self.df[self.vo]
            trace['name'] = 'Volume'
            trace['yaxis'] = 'y2'
            trace['showlegend'] = False

            # Determine if volume should be in 2 colors or in 1
            if type in OHLC_TRACES and self.has_open and self.has_close:
                volume_color = [
                    colors['increasing']
                    if (value - self.df[self.op].values[i]) >= 0
                    else colors['decreasing']
                    for i, value in enumerate(self.df[self.cl].values)
                ]
            else:
                volume_color = colors['primary']

            if type == 'candlestick':
                trace['marker']['color'] = volume_color
                trace['marker']['line']['color'] = colors['border']
            else:
                trace['marker']['color'] = volume_color
                trace['marker']['line']['color'] = volume_color

            data.append(trace)

        # Subplot volume delta
        if volume:
            delta = 1
        else:
            delta = 0

        # Plot secondary indicators
        for i, name in enumerate(self.sec):
            secondary = self.sec[name]
            trace = copy.deepcopy(traces[secondary['type']])

            trace['x'] = self.ind.index
            trace['y'] = self.ind[name]
            trace['name'] = name
            trace['yaxis'] = 'y' + str(i + delta + 2)

            trace['line']['color'] = colors[secondary['color']]

            if 'area' in secondary['type']:
                if 'fillcolor' in secondary:
                    trace['fillcolor'] = colors[secondary['fillcolor']]

            data.append(trace)

        # Modify layout

        # Axis
        layout['xaxis'] = copy.deepcopy(additions['xaxis'])
        layout['yaxis'] = copy.deepcopy(additions['yaxis'])

        # Subaxis
        if volume or self.sec:

            if len(self.sec) + delta == 1:
                layout['yaxis2'] = copy.deepcopy(additions['yaxis'])
                layout['yaxis']['domain'] = [0.30, 1.0]
                layout['yaxis2']['domain'] = [0.0, 0.25]

            elif len(self.sec) + delta == 2:
                layout['yaxis2'] = copy.deepcopy(additions['yaxis'])
                layout['yaxis3'] = copy.deepcopy(additions['yaxis'])
                layout['yaxis']['domain'] = [0.5, 1.0]
                layout['yaxis2']['domain'] = [0.25, 0.45]
                layout['yaxis3']['domain'] = [0.0, 0.20]

            else:
                print('Quantmod does not yet support plotting 3+ indicators.')

        # Margin
        if not layout['title']:
            layout['margin']['t'] = layout['margin']['b']

        # Subtitle
        if layout['showlegend'] and subtitle:

            if 'annotations' not in layout:
                layout['annotations'] = []

            if type in OHLC_TRACES:
                if (self.df[self.cl][-1] - self.df[self.op].values[-1]) >= 0:
                    annotations_color = colors['increasing']
                else:
                    annotations_color = colors['decreasing']
            else:
                annotations_color = colors['primary']

            last_price = dict(
                x = layout['legend']['x'],
                xanchor = layout['legend']['xanchor'],
                xref = 'paper',
                y = layout['legend']['y'],
                yanchor = layout['legend']['yanchor'],
                yref = 'paper',
                showarrow = False,
                text = 'Last {0:,.02f}'.format(self.df[self.cl][-1]),
                font = dict(color = annotations_color),
            )
            layout['annotations'].append(last_price)
            layout['legend']['y'] -= 0.03

            if volume:
                last_volume = dict(
                    x = layout['legend']['x'],
                    xanchor = layout['legend']['xanchor'],
                    xref = 'paper',
                    y = layout['yaxis2']['domain'][-1] - 0.01,
                    yanchor = layout['legend']['yanchor'],
                    yref = 'paper',
                    showarrow = False,
                    text = 'Volume {0:,}'.format(self.df[self.vo][-1]),
                    font = dict(color = annotations_color),
                )
                layout['annotations'].append(last_volume)

        figure = dict(data=data, layout=layout)
        return figure

    def plot(self, type=None, volume=None,
             theme=None, layout=None,
             title=None, subtitle=None, hovermode=None,
             legend=None, annotations=None, shapes=None,
             dimensions=None, width=None, height=None, margin=None,
             filename=None, online=None, **kwargs):
        """Generate a Plotly chart from Chart specifications.

        Parameters
        ----------
            type : {'ohlc', 'candlestick',
                    'line', 'line_thin', 'line_thick', 'line_dashed',
                    'line_dashed_thin', 'line_dashed_thick',
                    'area', 'area_dashed',
                    'area_dashed_thin', 'area_dashed_thick', 'area_threshold',
                    'scatter'}
                Determine the chart type of the main trace. For candlestick
                and OHLC bars Chart needs to have OHLC enabled.
            volume : bool
                Toggle the diplay of a volume subplot in chart.
            theme : string
                Quantmod theme.
            layout : dict or Layout
                Plotly layout dict or graph_objs.Layout object.
                Will override all other arguments if conflicting as
                user-inputted layout is updated last.
            title : string
                Chart title.
            subtitle : bool, default True
                Toggle the display of last price and/or volume in chart.
            hovermode : {'x', 'y', 'closest', False}
                Toggle how a tooltip appears on cursor hover.
            legend : dict, Legend or bool, default True
                True/False or Plotly legend dict / graph_objs.Legend object.
                If legend is bool, Quantmod will only toggle legend visibility.
            annotations : list or Annotations
                Plotly annotations list / graph.objs.Annotations object.
            shapes : list or Shapes
                Plotly shapes list or graph_objs.Shapes object.
            dimensions : tuple
                Dimensions 2-tuple in order (width, height).
                Disables autosize=True.
            width : int
                Width of chart.
                Disables autosize=True.
            height : int
                Height of chart.
                Disables autosize=True.
            margin : dict or tuple
                Plotly margin dict or 4-tuple in order (l, r, b, t) or
                5-tuple in order (l, r, b, t, margin). Tuple input added for
                Cufflinks compatibility.
            filename : string, default datetime.now()
                Filename of chart that will appear on plot.ly.
                By default, filename is set according to current system time.
            online : bool, default False
                If True, forces chart to be drawn online even if qm.go_offline()
                has been called.

        Examples
        --------
            ch = qm.Chart(df)
            ch.plot(type='ohlc', dimensions=(2560,1440))

            ch = qm.Chart(df)
            ch.add_BBANDS()
            ch.add_RSI(14)
            ch.plot(type='candlestick', title='EQUITY')

        """
        figure = self.to_figure(type=type, volume=volume,
                                theme=theme, layout=layout,
                                title=title, subtitle=subtitle,
                                hovermode=hovermode, legend=legend,
                                annotations=annotations, shapes=shapes,
                                dimensions=dimensions,
                                width=width, height=height,
                                margin=margin, **kwargs)

        # Default argument values

        # To be fixed ASAP: race condition if 2 plots made within 1 sec
        # Link filename generation to streambed API to prevent overwriting
        if filename is None:
            timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            filename = 'Quantmod Chart {0}'.format(timestamp)

        if online is None:
            online = False

        # Type checks for mandatorily used arguments
        if not isinstance(filename, six.string_types):
            raise TypeError("Invalid filename '{0}'. "
                            "It should be string."
                            .format(filename))

        if not isinstance(online, bool):
            raise TypeError("Invalid online '{0}'. "
                            "It should be bool."
                            .format(online))

        if tools.is_offline() and not online:
            show_link = tools.get_config_file()['offline_show_link']
            link_text = tools.get_config_file()['offline_link_text']
            return pyo.plot(figure, filename=filename,
                            show_link=show_link,
                            link_text=link_text)
        else:
            return py.plot(figure, filename=filename)

    def iplot(self, type=None, volume=None,
             theme=None, layout=None,
             title=None, subtitle=None, hovermode=None,
             legend=None, annotations=None, shapes=None,
             dimensions=None, width=None, height=None, margin=None,
             filename=None, online=None, **kwargs):
        """Generate a Plotly chart from Chart specifications.

        The iplot function returns an embedded chart suitable for Jupyter
        notebooks, while the plot function simply opens it in the browser.

        Parameters
        ----------
            type : {'ohlc', 'candlestick',
                    'line', 'line_thin', 'line_thick', 'line_dashed',
                    'line_dashed_thin', 'line_dashed_thick',
                    'area', 'area_dashed',
                    'area_dashed_thin', 'area_dashed_thick', 'area_threshold',
                    'scatter'}
                Determine the chart type of the main trace. For candlestick
                and OHLC bars Chart needs to have OHLC enabled.
            volume : bool
                Toggle the diplay of a volume subplot in chart.
            theme : string
                Quantmod theme.
            layout : dict or Layout
                Plotly layout dict or graph_objs.Layout object.
                Will override all other arguments if conflicting as
                user-inputted layout is updated last.
            title : string
                Chart title.
            subtitle : bool, default True
                Toggle the display of last price and/or volume in chart.
            hovermode : {'x', 'y', 'closest', False}
                Toggle how a tooltip appears on cursor hover.
            legend : dict, Legend or bool, default True
                True/False or Plotly legend dict / graph_objs.Legend object.
                If legend is bool, Quantmod will only toggle legend visibility.
            annotations : list or Annotations
                Plotly annotations list / graph.objs.Annotations object.
            shapes : list or Shapes
                Plotly shapes list or graph_objs.Shapes object.
            dimensions : tuple
                Dimensions 2-tuple in order (width, height).
                Disables autosize=True.
            width : int
                Width of chart.
                Disables autosize=True.
            height : int
                Height of chart.
                Disables autosize=True.
            margin : dict or tuple
                Plotly margin dict or 4-tuple in order (l, r, b, t) or
                5-tuple in order (l, r, b, t, margin). Tuple input added for
                Cufflinks compatibility.
            filename : string, default datetime.now()
                Filename of chart that will appear on plot.ly.
                By default, filename is set according to current system time.
            online : bool, default False
                If True, forces chart to be drawn online even if qm.go_offline()
                has been called.

        Examples
        --------
            ch = qm.Chart(df)
            ch.iplot(type='ohlc', dimensions=(2560,1440))

            ch = qm.Chart(df)
            ch.add_BBANDS()
            ch.add_RSI(14)
            ch.iplot(type='candlestick', title='EQUITY')

        """
        figure = self.to_figure(type=type, volume=volume,
                                theme=theme, layout=layout,
                                title=title, subtitle=subtitle,
                                hovermode=hovermode, legend=legend,
                                annotations=annotations, shapes=shapes,
                                dimensions=dimensions,
                                width=width, height=height,
                                margin=margin, **kwargs)

        # Default argument values
        if filename is None:
            timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            filename = 'Quantmod Chart {0}'.format(timestamp)

        if online is None:
            online = False

        # Type checks for mandatorily used arguments
        if not isinstance(filename, six.string_types):
            raise TypeError("Invalid filename '{0}'. "
                            "It should be string."
                            .format(filename))

        if not isinstance(online, bool):
            raise TypeError("Invalid online '{0}'. "
                            "It should be bool."
                            .format(online))

        if tools.is_offline() and not online:
            show_link = tools.get_config_file()['offline_show_link']
            link_text = tools.get_config_file()['offline_link_text']
            return pyo.iplot(figure, filename=filename,
                             show_link=show_link,
                             link_text=link_text)
        else:
            return py.iplot(figure, filename=filename)


Chart.add_SMA = add_SMA
Chart.add_EMA = add_EMA
Chart.add_WMA = add_WMA
Chart.add_DEMA = add_DEMA
Chart.add_TEMA = add_TEMA
Chart.add_KAMA = add_KAMA
Chart.add_TRIMA = add_TRIMA
Chart.add_MA = add_MA
#Chart.add_MAMA = add_MAMA
#Chart.add_MAVP = add_MAVP
Chart.add_BBANDS = add_BBANDS
#Chart.SAR = add_SAR
#Chart.SAREXT = add_SAREXT
#Chart.HT_TRENDLINE = add_HT_TRENDLINE
#Chart.T3 = add_T3
#Chart.add_midpoint =

Chart.add_RSI = add_RSI
#Chart.ADX = add_ADX
#Chart.ADXR = add_ADXR
#Chard.APO = add_APO
