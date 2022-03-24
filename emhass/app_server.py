#!/usr/bin/python

from flask import Flask, make_response, render_template
from jinja2 import Environment, FileSystemLoader
from requests import get
from pathlib import Path
import os, json
from emhass.command_line import setUp
from emhass.command_line import dayahead_forecast_optim
from emhass.command_line import publish_data

app = Flask(__name__)
app.env = "development"

OPTIONS_PATH = "/data/options.json"
options_json = Path(OPTIONS_PATH)
CONFIG_PATH = "/app/config_emhass.json"
config_path = Path(CONFIG_PATH)
base_path = str(config_path.parent)

# Read options info
if options_json.exists():
    with options_json.open('r') as data:
        options = json.load(data)
else:
    app.logger.error("ERROR: options.json does not exists")

# Read example config file
if config_path.exists():
    with config_path.open('r') as data:
        config = json.load(data)
    retrieve_hass_conf = config['retrieve_hass_conf']
    optim_conf = config['optim_conf']
    plant_conf = config['plant_conf']
else:
    app.logger.error("ERROR: config_emhass.json does not exists")

# Build params and params_secrets
hass_url = 'http://supervisor/core/api'
long_lived_token = '${SUPERVISOR_TOKEN}'
url = hass_url+"/config"
headers = {
    "Authorization": "Bearer " + long_lived_token,
    "content-type": "application/json"
}
response = get(url, headers=headers)
try:
    config_hass = response.json()
except IndexError:
    app.logger.error("The retrieved JSON is empty, check that correct url and token are passed")
params_secrets = {
    'hass_url': hass_url,
    'long_lived_token': long_lived_token,
    'time_zone': config_hass['time_zone'],
    'lat': config_hass['latitude'],
    'lon': config_hass['longitude'],
    'alt': config_hass['elevation']
}
# Updating variables in retrieve_hass_conf
retrieve_hass_conf[0]['freq'] = options['optimization_time_step']
retrieve_hass_conf[0]['days_to_retrieve'] = options['historic_days_to_retrieve']
retrieve_hass_conf[0]['var_PV'] = options['sensor_power_photovoltaics']
retrieve_hass_conf[0]['var_load'] = options['sensor_power_load_no_var_loads']
retrieve_hass_conf[0]['var_replace_zero'] = [options['sensor_power_photovoltaics']]
retrieve_hass_conf[0]['var_interp'] = [options['sensor_power_photovoltaics'], options['sensor_power_load_no_var_loads']]
# Updating variables in optim_conf
optim_conf[0]['set_use_battery'] = options['set_use_battery']
optim_conf[0]['num_def_loads'] = options['number_of_deferrable_loads']
optim_conf[0]['P_deferrable_nom'] = [int(i) for i in options['nominal_power_of_deferrable_loads'].split(',')]
optim_conf[0]['def_total_hours'] = [int(i) for i in options['operating_hours_of_each_deferrable_load'].split(',')]
optim_conf[0]['treat_def_as_semi_cont'] = [True for i in range(len(optim_conf[0]['P_deferrable_nom']))]
optim_conf[0]['set_def_constant'] = [False for i in range(len(optim_conf[0]['P_deferrable_nom']))]
# TODO: implement weather forecast, load, prod sell price and load cost forecast methods using CSV (load CSV files with new function with POST method)
optim_conf[0]['list_hp_periods'] = json.loads(options['peak_hours_periods_data'])
optim_conf[0]['load_cost_hp'] = options['load_peak_hours_cost']
optim_conf[0]['load_cost_hc'] = options['load_offpeak_hours_cost']
optim_conf[0]['prod_sell_price'] = options['photovoltaic_production_sell_price']
# Updating variables in plant_conf
plant_conf[0]['P_grid_max'] = options['maximum_power_from_grid']
plant_conf[0]['module_model'] = options['pv_module_model']
plant_conf[0]['inverter_model'] = options['pv_inverter_model']
plant_conf[0]['surface_tilt'] = options['surface_tilt']
plant_conf[0]['surface_azimuth'] = options['surface_azimuth']
plant_conf[0]['modules_per_string'] = options['modules_per_string']
plant_conf[0]['strings_per_inverter'] = options['strings_per_inverter']
plant_conf[0]['Pd_max'] = options['battery_discharge_power_max']
plant_conf[0]['Pc_max'] = options['battery_charge_power_max']
plant_conf[0]['eta_disch'] = options['battery_discharge_efficiency']
plant_conf[0]['eta_ch'] = options['battery_charge_efficiency']
plant_conf[0]['Enom'] = options['battery_nominal_energy_capacity']
plant_conf[0]['SOCmin'] = options['battery_minimum_state_of_charge']
plant_conf[0]['SOCmax'] = options['battery_maximum_state_of_charge']
plant_conf[0]['SOCtarget'] = options['battery_target_state_of_charge']


@app.route('/')
def hello():
    app.logger.info("EMHASS server online...")
    # Load HTML template
    # file_loader = FileSystemLoader('templates')
    # env = Environment(loader=file_loader)
    # template = env.get_template('index.html')
    # Get full path to image
    # image_path_0 = fig.to_html(full_html=False, default_width='75%')
    # The tables
    # table1 = overview_df.reset_index().to_html(classes='mystyle', index=False)
    # The dict of plots
    # injection_dict = {}
    # injection_dict['title'] = '<h2>EMHHAS optimization results</h2>'
    # injection_dict['subsubtitle1'] = '<h4>Last run results</h4>'
    # injection_dict['table1'] = table1
    # injection_dict['subsubtitle2'] = '<h4>Plotting</h4>'
    # injection_dict['figure_0'] = image_path_0
    # Render HTML template with elements from report
    # source_html = template.render(injection_dict=injection_dict)
    # return render_template(source_html)
    return render_template('index.html')

@app.route('/action/<name>', methods=['POST'])
def action_call(name):
    if name == 'publish-data':
        app.logger.info("Publishing data...")
    elif name == 'dayahead-optim':
        app.logger.info("Performing optimization...")
    else:
        app.logger.error("ERROR: passed action is not valid")

    msg = f'EMHASS >> Action {name} received\n'
    return make_response(msg, 201)

if __name__ == "__main__":
    os.environ.setdefault('FLASK_ENV', 'development')
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)