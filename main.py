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
import random
import shower
import user
import numpy as np

def days_to_seconds(days):
    return days * 86400

def hours_to_seconds(hours):
    return hours * 3600

def generate_period(time_step, period_length=1):
    if period_length < 1:
        period_length = 1
    
    return int(period_length * 86400/time_step)

#SIMULATION SETTINGS
# set number of simulation days
simulation_days = 10000
# simulation time steps defined in seconds
time_step = 60
# define single simulation time period
sim_period = generate_period(time_step, 1)
sim_duration = sim_period * simulation_days
# extract real temperature data from CSV file to dataframe 
temp_profile_df = pd.read_csv("data/measured_temperatures/historical_temp_2019_2022.csv", header=0, infer_datetime_format=True, parse_dates=['datetime'], index_col='datetime')
temp_profile_df.index = pd.to_datetime(temp_profile_df.index)
# define containers to contain EWH temperature(s) and power
ewh_temp = []
ewh_power = []
ewh_draw = []

# instantiate EWH object
ewh = ewh_sim.EWH(always_on=True, randomised=False)
ewh.initialise_temp()

# instantitate and initialise simulation settings and ambient temp value
sim = ewh_sim.Simulation(days=simulation_days, temp_variance=True, time_step=time_step)
ambient_temp = sim.ambient_temperature

# instantiate user and shower
user = user.User(age='work_ad')
shower = shower.Shower()

# set containers for simulated EWH temperature, power and event time periods
activation_periods = []
draw_event_periods = []
start_times = []

# set container for simulated EWH settings
ewh_settings = [ewh.mass, ewh.element_rating, ewh.upper_temp_limit, ewh.lower_temp_limit]
    
# if temperature variance is active, initialise ambient EWH temp from measured data
if sim.temp_variance:
   # initialise simulation ambient temp
   sim.ambient_temperature = temp_profile_df.iloc[0]["temperature_2m (°C)"]
   # set the date-time stamp for the next ambient temp value
   ambient_stamp = temp_profile_df.index[0] + DateOffset(hours=1)

# for simulation_day in range(simulation_days):
# set EWH temp control to run continuously
if ewh.always_on:
    ewh.is_active = True
    
#RUN SIMULATION 
for sim_day in range(simulation_days):
    # run shower usage simulation
    start_time, end_time, intensity = shower.simulate(user)
    start_times.append(start_time)
    
    #generate EWH temperature profile
    for period in range (sim_period):
        #every hour update the ambient temp using real temp data
        if sim.temp_variance and period%60==0:
            try:
                sim.ambient_temperature = temp_profile_df.loc[ambient_stamp]["temperature_2m (°C)"]
                ambient_stamp = ambient_stamp + DateOffset(hours=1)
            except:
                sim.ambient_temperature = temp_profile_df.iloc[0]["temperature_2m (°C)"]
                ambient_stamp = temp_profile_df.index[0] + DateOffset(hours=1)
            
            
            
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
            ewh_draw.append(intensity*60)
        else:
            ewh_draw.append(0)
        
        #determine temperature change due to ewh element
        if ewh.is_active:
            if ewh.element_on:
                if ewh.current_temp < ewh.upper_temp_limit:
                    ewh.current_temp = ewh.increase_temp(sim.time_step)
                    ewh_power.append(ewh.element_rating)
                else:
                    #print(pd.Timedelta(minutes=period))
                    ewh.element_on = False
                    ewh_power.append(0)
            else:
                if ewh.current_temp < ewh.lower_temp_limit:
                    #print(pd.Timedelta(minutes=period))
                    ewh.element_on = True
                    ewh.current_temp = ewh.increase_temp(sim.time_step)
                    ewh_power.append(ewh.element_rating)
                else:
                    ewh_power.append(0)
        else:
            ewh_power.append(0)
        
        ewh_temp.append(ewh.current_temp)


display_plot = False
display_pdf_hist = True

if display_plot:
    #INITIALISE DATAFRAME TO STORE SIMULATION RESULTS
    # restrict number of samples when plotting results for readability
    # default is 24-hours worth of samples assuming minutely time steps
    plotting_limit = 1440
    
    # define date-time range
    # date-time starts at midnight of the first day of the year
    # minimum period is 24-hours
    sim_datetime = pd.date_range('2024-01-01 00:00:00', periods=sim_duration, 
                                 freq="{0}s".format(time_step))
    # initialise and populate dataframe index and columns
    sim_df = pd.DataFrame(index=sim_datetime)
    sim_df.index.name = 'datetime'
    sim_df_column_names = ['EWH Temperature (C)', 'EWH Power (kW)', 'Draw Volume (l/min)']
    sim_df['EWH Temperature (C)'] = ewh_temp
    sim_df['EWH Power (kW)'] = [power/1000 for power in ewh_power]
    sim_df['Draw Volume (l/min)'] = ewh_draw
        
    #PLOT EWH SIMULATION RESULTS
    # figure display settings
    date_format = DateFormatter("%H:%M")
    plt.rcParams['figure.dpi'] = 300
    
    # define plot figure
    sim_fig, temp_ax = plt.subplots(1, figsize=(18, 7))
    
    #plot simulation results
    temp_ax.set_title("{0}-day EWH Simulation Results".format(simulation_days))
    temp_ax.set_xlabel('Time')
    temp_ax.set_ylabel('Temperature (C)')
    temp_ax.margins(x=0.001, y=0.02)
    temp_ax.xaxis.set_major_formatter(date_format)
    temp_ax.plot(sim_df['EWH Temperature (C)'])
    plt.ylim(0, ewh.upper_temp_limit+1)
    
    power_ax = temp_ax.twinx() 
    power_ax.plot(sim_df['EWH Power (kW)'], color='tab:red')
    power_ax.set_ylabel('Power (kW)')
    power_ax.margins(x=0.002, y=0.02)
    sim_fig.tight_layout()
    
    # draw_ax = temp_ax.twinx() 
    # draw_ax.plot(sim_df['Draw Volume (l/min)'], color='tab:red')
    # draw_ax.set_ylabel('Volume (l/min)')
    # sim_fig.tight_layout()
    
    #SAVE SIMULATIONS TO FILE
    sim_df.to_csv("simulation_results/{0}_day_ewh_simulation.csv".format(simulation_days))

if display_pdf_hist:
    plt.hist(start_times)
    pdf = user.schedule.pdf
    cdf = np.cumsum(pdf)
    
    #PLOT EWH SIMULATION RESULTS
    # figure display settings
    date_format = DateFormatter("%H:%M")
    plt.rcParams['figure.dpi'] = 300

    # define plot figure
    cdf_fig, cdf_ax = plt.subplots(1, figsize=(18, 7))

    #plot simulation results
    cdf_ax.set_title('Water Usage PDF vs CDF')
    cdf_ax.set_xlabel('Time')
    cdf_ax.set_ylabel('Probability Water Usage (CDF)')
    cdf_ax.margins(x=0.002, y=0.02)
    #cdf_ax.xaxis.set_major_formatter(date_format)
    cdf_ax.plot(np.cumsum(pdf))

    pdf_ax = cdf_ax.twinx() 
    pdf_ax.plot(pdf, color='tab:red')
    pdf_ax.set_ylabel('Probability Water Usage (PDF)')
    pdf_ax.margins(x=0.002, y=0.02)
    #pdf_ax.xaxis.set_major_formatter(date_format)
    cdf_fig.tight_layout()
    
# save EWH power profile to CSV 
#ewh_power_df.to_csv("training_data/simulated_profiles/{0}_day_ewh_power_profiles.csv".format(simulation_days))

