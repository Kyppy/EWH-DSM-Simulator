# -*- coding: utf-8 -*-
"""
Created on Tue Apr  4 10:35:00 2023

@author: Kyppy
"""
import math
import random
specific_heat_cap = 4180

class EWH: 
    def __init__(self, always_on=False, element_rating=3000, draw_rate=15, 
                 inlet_temp=25, mass=150, randomised=False, thermal_conduct=0.341, 
                 upper_temp_limit=60, lower_temp_limit=50, volume=150):
        self.activation_timer = 0
        self.always_on = always_on
        self.current_temp = 25.2
        self.draw_event = False
        self.draw_rate = draw_rate/60
        self.element_on = False
        self.element_rating = element_rating
        self.full_draw_duration = (volume/draw_rate) * 60
        self.inlet_temp = inlet_temp
        self.is_active = False
        self.lower_temp_limit = lower_temp_limit
        self.mass = mass
        self.randomised = randomised
        self.thermal_conduct = thermal_conduct
        self.upper_temp_limit = upper_temp_limit
        self.volume = volume
        
    def calculate_alpha(self, time_step):
        return (-1*time_step)/(specific_heat_cap*self.mass*self.thermal_conduct)
    
    def calculate_power(self, delta_temp, time_step):
        return ((self.mass * specific_heat_cap * delta_temp)/time_step)
    
    def draw_event_loss (self, draw_rate=None, time_step=60):
        if draw_rate is None:
            draw_rate = self.draw_rate
        sigma = (self.volume - (draw_rate*time_step))/self.volume
        return sigma * (self.current_temp - self.inlet_temp) + self.inlet_temp
    
    def initialise_temp(self):
        self.element_on = random.choices([True, False], [0.04, 0.96], k=1)[0]
        self.current_temp = round(random.uniform(self.lower_temp_limit, self.upper_temp_limit), 2)
        
    def increase_temp(self, time_step):
        energy = self.element_rating * time_step
        return (energy)/(specific_heat_cap*self.mass) + self.current_temp
    
    def randomise_settings(self):
        self.element_rating = random.choice([2000, 3000, 4000])
        self.mass = random.choice([100, 150, 200, 250])
        self.thermal_conduct = round(random.uniform(0.30, 0.65), 2)
        self.upper_temp_limit = round(random.uniform(56, 71), 2)
        self.lower_temp_limit = self.upper_temp_limit - round(random.uniform(1, 5), 2)
        self.current_temp = round(random.uniform(self.lower_temp_limit, self.upper_temp_limit), 2)
    
    def standing_loss (self, ambient_temperature, time_step):
        alpha = self.calculate_alpha(time_step)
        return ambient_temperature + ((self.current_temp-ambient_temperature)*math.exp(alpha))

class Simulation:
    def __init__(self, activation_limit=150, ambient_temperature=25.2, days=5, 
                 draw_event_limits=(7, 20), draw_event_frequency=180, 
                 event_timer=0, cycle_refresh_rate= 24, draw_volume=50, 
                 event_average=8, temp_variance=False, time_step=5):
        self.activation_limit = int((activation_limit*60)/time_step)
        self.ambient_temperature = ambient_temperature
        self.days = days
        self.day_periods = int(days*24*(3600/time_step))
        self.draw_event_durations = range(draw_event_limits[0]*12, (draw_event_limits[1]*12)+1)
        self.draw_event_frequency = int((draw_event_frequency*60)/time_step)
        self.draw_volume = draw_volume
        self.event_timer = event_timer
        self.cycle_refresh_period = (cycle_refresh_rate * 3600)/time_step
        self.event_average = event_average
        self.temp_variance = temp_variance
        self.time_step = time_step
        self.time_scale = int((3600/time_step))
        
    def constrained_sum_sample_pos(self, n, total):
        """Return a randomly chosen list of n positive integers summing to total.
        Each such list is equally likely to occur."""

        dividers = sorted(random.sample(range(1, total), n - 1))
        return [a - b for a, b in zip(dividers + [total], [0] + dividers)]
    
    def chunk_event_periods(self):
        total_periods = int((self.days*86400)/self.time_step)
        event_periods = range(total_periods)
        day_period = int((24*60*60)/self.time_step)
        chunked_periods = [event_periods[i:i + day_period] for i in range(0, len(event_periods), day_period)]
        return chunked_periods
        
    def is_draw_period(self, time_period):
        if time_period%self.draw_event_frequency == 0:
            return True
        else:
            return False
    
    def refresh_event_timer (self):
        self.event_timer += random.choice(self.draw_event_durations)
    
    def refresh_max_events(self, time_period):
        if time_period%self.cycle_refresh_rate == 0:
            return True
        else:
            return False
    
    def daily_event_distribution (self):
        event_total = (self.days * self.event_average)
        return self.constrained_sum_sample_pos(self.days, event_total)
    
    def generate_daily_random_draw_periods(self):
        daily_event_periods = self.chunk_event_periods()
        draw_periods = []
        
        for daily_period in daily_event_periods:
            draw_periods.append(random.choice(daily_period))
        
        return draw_periods
    
    def generate_bounded_draw_periods(self, start_hour=6, end_hour=8):
        start_period = start_hour * self.time_scale
        end_period = end_hour*self.time_scale
        
        bounded_periods = []
        for i in range(0, self.day_periods, int(24*self.time_scale)):
            event_bounds = range(start_period + i, end_period + i)
            bounded_periods.append(random.choice(event_bounds))
        
        return bounded_periods
        
    def generate_event_pool(self):
        daily_event_frequency = self.daily_event_distribution()
        event_times = self.chunk_event_periods()

        event_pool = []
        for event_frequency, event_times in zip(daily_event_frequency,event_times):
            event_pool += random.sample(event_times, event_frequency)
        return event_pool
    
    def generate_activation_timing(self):
        event_periods = self.chunk_event_periods()
        activation_timing = []
        for event_period in event_periods:
            activation_timing += random.sample(event_period, 2)
        return activation_timing
    
    def generate_activation_time(self):
        return random.choice(range(self.activation_limit))
    
    def generate_time_periods(self):
        return int((self.days*86400)/self.time_step)
    