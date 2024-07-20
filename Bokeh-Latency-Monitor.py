import re
import math
from pythonping import ping
from bokeh.plotting import figure, show, curdoc
from bokeh.models import ColumnDataSource, DatetimeTickFormatter, PolySelectTool, SaveTool, HoverTool
from bokeh.layouts import column
from bokeh.io import push_notebook
import pandas as pd

#____________________________________________________________________________________________________________________________
# Extract target IPs from the text file

def extract_targets_from_config(file_path):
    targets = []
    with open(file_path, 'r') as file:
        config = file.read()
        matches = re.findall(r'host\s*=\s*([\d\.]+)', config)
        targets = [match for match in matches]
    return targets

#____________________________________________________________________________________________________________________________
# Create a plot for a single host

def create_host_plot(host):
    default_tools = ["pan", "box_zoom", "wheel_zoom", "reset"]
    additional_tools = ["poly_select", "save"]
    tools = default_tools + additional_tools

    plot = figure(x_axis_type="datetime", title=f"Latency - {host}", width=800, height=400, tools=tools)

    # Add HoverTool with tooltips
    hover = HoverTool(tooltips=[("Time", "@x{%F %H:%M:%S}"), ("Latency", "@y{0} ms")],
                      formatters={'@x': 'datetime'},
                      mode='vline')
    plot.add_tools(hover)

    plot.yaxis.axis_label = "Latency (ms)"
    plot.xaxis.formatter = DatetimeTickFormatter(seconds="%H:%M:%S")
    plot.xaxis.axis_label = "Time"
    return plot

#____________________________________________________________________________________________________________________________
# Ping a target and return latency and packet loss

def ping_target(target):
    responses = ping(target, count=4, timeout=4, verbose=False)  

    # Check if there were successful responses
    if responses.rtt_min is None:
        return None, 100.0  # 100% packet loss

    avg_latency = responses.rtt_avg
    avg_latency = round(avg_latency * 1000)  

    return avg_latency, responses.packet_loss * 100.0

#____________________________________________________________________________________________________________________________
# Update the graph for a single host

def update(host, plot, source):
    now = pd.to_datetime('now')
    avg_latency, packet_loss = ping_target(host)

    # Update latency plot
    if avg_latency is not None:
        source.stream(dict(x=[now], y=[avg_latency if packet_loss < 100 else math.nan]))

        if avg_latency > 1.5 * source.data['y'][-1]:
            plot.line(x='x', y='y', source=source, line_width=2, alpha=0.8, line_join='round', legend_label=host, line_color="red")
        else:
            plot.line(x='x', y='y', source=source, line_width=2, alpha=0.8, line_join='round', legend_label=host, line_color="blue")

    push_notebook()

#____________________________________________________________________________________________________________________________
# Initialize Bokeh plots and data sources

targets = extract_targets_from_config("server_ips_config.txt")  
plots = {}  
sources = {}  

for target in targets:
    plot = create_host_plot(target)
    source = ColumnDataSource(data=dict(x=[], y=[]))
    plot.line(x='x', y='y', source=source, line_width=2, alpha=0.8, line_join='round', legend_label=target)
    plots[target] = plot
    sources[target] = source

layout = column(list(plots.values()))
curdoc().add_root(layout)
curdoc().title = "Latency Graphs"
curdoc().theme = 'dark_minimal'

# Update the graphs for each host
for target, plot, source in zip(targets, plots.values(), sources.values()):
    curdoc().add_periodic_callback(lambda t=target, p=plot, s=source: update(t, p, s), 1000)  

show(layout, notebook_handle=True)