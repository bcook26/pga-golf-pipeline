# from routers import weather_api

from dash import Dash, html
from dash import dcc
from dash.dependencies import Input, Output

app = Dash(__name__, title='Golf ETL Dashboard')

# Define the layout for each page
def home_layout() -> html.Div:
    """ Layout for the Home page. """
    return html.Div([
        html.H1('Golf ETL Dashboard', style={'textAlign': 'center'}),
        html.P('A dashboard to monitor Golf ETL processes and WeatherAPI data.', style={'textAlign': 'center'}),
    ], style={'padding': '20px'})

def weather_layout() -> html.Div:
    """ Layout for the Weather Data page. """
    return html.Div([
        html.H2('Weather Data', style={'textAlign': 'center'}),
        html.Div(id='weather-data')
    ], style={'padding': '20px'})

def etl_layout() -> html.Div:
    """ Layout for the ETL Process Data page. """
    return html.Div([
        html.H2('ETL Process Data', style={'textAlign': 'center'}),
        html.Div(id='etl-process-data')
    ], style={'padding': '20px'})

def course_layout() -> html.Div:
    """ Layout for the Course Data page. """
    return html.Div([
        html.H2('Course Data', style={'textAlign': 'center'}),
        html.Div(id='course-data')
    ], style={'padding': '20px'})

# Multi-page layout with sidebar navigation
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div([
        html.Div([
            dcc.Link('Home', href='/', style={'display': 'block', 'marginBottom': '20px'}),
            dcc.Link('Weather', href='/weather', style={'display': 'block', 'marginBottom': '20px'}),
            dcc.Link('ETL', href='/etl', style={'display': 'block', 'marginBottom': '20px'}),
            dcc.Link('Course', href='/course', style={'display': 'block'}),
        ], style={
            'width': '180px',
            'padding': '20px',
            'background': '#f4f4f4',
            'height': '100vh',
            'position': 'fixed',
            'top': 0,
            'left': 0
        }),
        html.Div(id='page-content', style={'marginLeft': '200px', 'padding': '20px'})
    ], style={'display': 'flex'})
])

@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname: str) -> html.Div:
    """ Display the appropriate page layout based on the URL pathname. """
    if pathname == '/weather':
        return weather_layout()
    elif pathname == '/etl':
        return etl_layout()
    elif pathname == '/course':
        return course_layout()
    else:
        # Default to home page
        return home_layout()

if __name__ == '__main__':
    app.run(debug=True)