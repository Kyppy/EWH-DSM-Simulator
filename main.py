# -*- coding: utf-8 -*-
"""
Created on Mon Sep  2 13:04:24 2024

@author: Kyppy
"""

import ewh_sim
import math
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import pandas as pd
from pandas.tseries.offsets import DateOffset
import shower
import user

def days_to_seconds(days):
    return days * 86400

def hours_to_seconds(hours):
    return hours * 3600

def generate_period(simulation_duration, time_step):
    if simulation_duration < 1:
        simulation_duration = 1
    
    return int(simulation_duration * 86400/time_step)

#SIMULATION SETTINGS
# set number of simulation days
simulation_days = 1
# simulation time steps defined in seconds
time_step = 60
# define single simulation time period
sim_period = generate_period(simulation_days, time_step)
# extract real temperature data from CSV file to dataframe 
temp_profile_df = pd.read_csv("data/measured_temperatures/historical_temp_2019_2022.csv", header=0, infer_datetime_format=True, parse_dates=['datetime'], index_col='datetime')
temp_profile_df.index = pd.to_datetime(temp_profile_df.index)
# define containers to contain EWH temperature(s) and power
ewh_temp = []
ewh_power = []

# instantiate EWH object
ewh = ewh_sim.EWH(always_on=True, randomised=False)
# instantitate and initialise simulation settings and ambient temp value
sim = ewh_sim.Simulation(days=simulation_days, temp_variance=True, time_step=time_step)
ambient_temp = sim.ambient_temperature

# instantiate user and shower
user = user.User(age='work_ad')
shower = shower.Shower()
# run single shower simulation
start_time, end_time, intensity = shower.simulate(user)

print(pd.Timedelta(minutes=start_time))
#RUN SIMULATION 
for sim_day in range(simulation_days):
    # set containers for simulated EWH temperature, power and event time periods
    temp = []
    power = []
    activation_periods = []
    draw_event_periods = []
    
    # set container for simulated EWH settings
    ewh_settings = [ewh.mass, ewh.element_rating, ewh.upper_temp_limit, ewh.lower_temp_limit]
        
    # if temperature variance is active, initialise ambient EWH temp from real temp data
    if sim.temp_variance:
       # initialise simulation ambient temp
       sim.ambient_temperature = temp_profile_df.iloc[0]["temperature_2m (°C)"]
       # set the date-time stamp for the next ambient temp value
       ambient_stamp = temp_profile_df.index[0] + DateOffset(hours=1)
    
    # for simulation_day in range(simulation_days):
    # set EWH temp control to run continuously
    if ewh.always_on:
        ewh.is_active = True
    
    #generate EWH temperature profile
    for period in range (sim_period):
        #every hour update the ambient temp using real temp data
        if sim.temp_variance and period%60==0:
            sim.ambient_temperature = temp_profile_df.loc[ambient_stamp]["temperature_2m (°C)"]
            ambient_stamp = ambient_stamp + DateOffset(hours=1)
            
        #determine temperature change due to standing losses
        ewh.current_temp = ewh.standing_loss(sim.ambient_temperature, sim.time_step)
        
        # check for draw event start and end times
        if period == start_time:
            ewh.draw_event  = True
        elif period == end_time:
            ewh.draw_event  = False
        
        # perform draw event
        if ewh.draw_event:
            ewh.current_temp = ewh.draw_event_loss(draw_rate=intensity)
        
        #determine temperature change due to ewh element
        if ewh.is_active:
            if ewh.element_on:
                if ewh.current_temp < ewh.upper_temp_limit:
                    ewh.current_temp = ewh.increase_temp(sim.time_step)
                    power.append(ewh.element_rating)
                else:
                    ewh.element_on = False
                    power.append(0)
            else:
                if ewh.current_temp < ewh.lower_temp_limit:
                    ewh.element_on = True
                    ewh.current_temp = ewh.increase_temp(sim.time_step)
                    power.append(ewh.element_rating)
                else:
                    power.append(0)
        else:
            power.append(0)
        
        temp.append(ewh.current_temp)
    # add current EWH temperature to list of other simulated EWH temperatures
    ewh_temp.append(temp)
    # add current EWH power to list of other simuated EWH power
    ewh_power.append(power)
    
    # # add current EWH settings to settings dataframe
    # ewh_df.loc[len(ewh_df.index)] = ewh_settings


#INITIALISE DATAFRAME TO STORE SIMULATION RESULTS
# restrict number of samples when plotting results for readability
# default is 24-hours worth of samples assuming minutely time steps
plotting_limit = 1440

# define date-time range
# date-time starts at midnight of the first day of the year
# minimum period is 24-hours
sim_datetime = pd.date_range('2024-01-01 00:00:00', periods=sim_period, 
                             freq="{0}s".format(time_step))
# initialise and populate dataframe index and columns
sim_df = pd.DataFrame(index=sim_datetime)
sim_df.index.name = 'datetime'
sim_df_column_names = ['EWH Temperature (\u2103)', 'EWH Power (kW)']
sim_df['EWH Temperature (\u2103)'] = ewh_temp[0]
sim_df['EWH Power (kW)'] = [power//1000 for power in ewh_power[0]]
    
#PLOT EWH SIMULATION RESULTS
# figure display settings
date_format = DateFormatter("%H:%M")
plt.rcParams['figure.dpi'] = 300

# define plot figure
sim_fig, sim_ax = plt.subplots(1, figsize=(18, 7))

#plot simulation results
sim_ax.set_title('EWH Sim Results')
sim_ax.set_xlabel('Time')
sim_ax.set_ylabel('Temperature (\u2103)')
sim_ax.margins(x=0.001, y=0.02)
sim_ax.xaxis.set_major_formatter(date_format)
sim_ax.plot(sim_df['EWH Temperature (\u2103)'])

ax2 = sim_ax.twinx() 

ax2.plot(sim_df['EWH Power (kW)'], color='tab:red')
ax2.set_ylabel('Power (kW)')
sim_fig.tight_layout()

#SAVE SIMULATIONS TO FILE
# save EWH temperature profiles to CSV 
#ewh_temp_df.to_csv("training_data/simulated_profiles/{0}_day_ewh_temp_profiles.csv".format(simulation_days))

# save EWH power profile to CSV 
#ewh_power_df.to_csv("training_data/simulated_profiles/{0}_day_ewh_power_profiles.csv".format(simulation_days))

