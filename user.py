import os
import toml
import copy
import numpy as np
import scipy.stats as sci_stats
import pandas as pd
import matplotlib.pyplot as plt
import utils
from matplotlib.dates import DateFormatter
from dataclasses import dataclass, field
from typing import Any, Callable, Literal
from settings import DATA_PATH
import random
@dataclass
class UserSchedule:
    """Class representing the user activity schedule."""

    weekday: bool
    user: Any
    
    up: pd.Timedelta = field(init=False)
    go: pd.Timedelta = field(init=False)
    home: pd.Timedelta = field(init=False)
    sleep: pd.Timedelta = field(init=False)
    pdf: Any = field(init=False, repr=False)
    cdf: Any = field(init=False, repr=False)

    # store probability distributions for each state of activity 
    _prob_getting_up: Any = field(init=False, repr=False)
    _prob_leaving_house: Any = field(init=False, repr=False)
    _prob_being_away: Any = field(init=False, repr=False)
    _prob_sleep: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:

        diurnal_stats = toml.load(open(os.path.join(DATA_PATH, 'diurnal_distributions.toml'), 'r'))
        if self.weekday:
            diurnal_pattern = diurnal_stats[self.user.age]
        else:
            diurnal_pattern = diurnal_stats['weekend']

        for key, val in diurnal_pattern.items():
            dist = val['dist']
            dist = getattr(sci_stats, dist)
            mean = round(pd.Timedelta(val['mu']).total_seconds() / 60)
            std_dev = round(pd.Timedelta(val['sd']).total_seconds() / 60)
            setattr(self, '_prob_' + key, dist(loc=mean, scale=std_dev))

        self.up = self.sample_single_property('_prob_getting_up')

        self.sleep = self.sample_single_property('_prob_getting_up') - self.sample_single_property('_prob_sleep') + pd.Timedelta(days=1)
    
        self.go = self.sample_single_property('_prob_leaving_house')
        
        if self.go < self.up:
            self.go = self.up + pd.Timedelta(minutes=30)

        self.home = self.go + self.sample_single_property('_prob_being_away')
        
        if self.home < self.go:
            # did not leave homes
            self.home = self.go  

        if self.sleep < self.home:
            self.home = self.sleep - pd.Timedelta(minutes=30)
    
    def generate_pdf(self, peak=0.65, normal=0.335, away=0.0, night=0.015):
        index = pd.timedelta_range(start='00:00:00', end='23:59:00', freq='1Min')
        pdf = pd.Series(index=index, dtype='float64')
        
        up = int((self.up.total_seconds()) / 60) % 1440
        up_p30 = int((up + 30)) % 1440

        go = int(self.go.total_seconds() / 60) % 1440
        go_m30 = int(go - 30) % 1440

        home = int(self.home.total_seconds() / 60) % 1440
        home_p30 = int(home + 30) % 1440

        sleep_day, sleep = divmod(int(self.sleep.total_seconds() / 60), 1440)
        if sleep_day >= 1:
            sleep_m30 = int(1440-30) % 1440
        else:
            sleep_m30 = int(sleep - 30) % 1440

        pdf = self.timeindexer(pdf, 'normal', up_p30, go_m30)
        pdf = self.timeindexer(pdf, 'peak', up, up_p30)
        pdf = self.timeindexer(pdf, 'peak', go_m30, go)
        pdf = self.timeindexer(pdf, 'peak', home, home_p30)
        pdf = self.timeindexer(pdf, 'away', go, home)
        
        if sleep_day >= 1:
            pdf = self.timeindexer(pdf, 'normal', home_p30, 1440)
            pdf = self.timeindexer(pdf, 'night', 1440, up)
        else:
            pdf = self.timeindexer(pdf, 'normal', home_p30, sleep_m30)
            pdf = self.timeindexer(pdf, 'peak', sleep_m30, sleep)
            pdf = self.timeindexer(pdf, 'night', sleep, up)
        
        try:
            pdf[pdf == 'peak'] = peak 
        except:
            pass
        try:
            pdf[pdf == 'normal'] = normal 
        except:
            pass
        try:
            pdf[pdf == 'night'] = night 
        except:
            pass
        try:
            pdf[pdf == 'away'] = 0.0
        except:
            pass
       
        # normalize stats to produce pdf
        pdf /= np.sum(pdf)  
        
        return pdf
            
    def sample_single_property(self, prop: str) -> pd.Timedelta:
        """Function to draw random time values from the single time properties (e.g., getting up, leave house, ...) of the users"""
    
        prob_fct = getattr(self, prop)
        x = prob_fct.rvs()
        x = int(np.round(x))
        x = pd.Timedelta(minutes=x)
        return x
    
    def timeindexer(self, l, value, a, b):

        if a < b:
            l[a:b] = value
        else:
            l[a:len(l)] = value
            l[0:b] = value
        return l

@dataclass
class User:

    #gender: Literal['male', 'female'] = None
    age: Literal['child', 'teen', 'adult', 'home_ad', 'work_ad', 'senior'] = None  
    job: bool = True
    schedule: UserSchedule = field(init=False, repr=False)
    
    def __post_init__(self):

        if self.age == 'adult':
            if self.job:
                self.age = 'work_ad'
            else:
                self.age = 'home_ad'
        
        self.generate_pdf()
        self.schedule.cdf = np.cumsum(self.schedule.pdf)

    def generate_schedule(self, weekday=True):
        self.schedule = UserSchedule(user=self, weekday=weekday)
    
    def generate_pdf(self, peak=0.65, normal=0.335, away=0.0, night=0.015):
        self.generate_schedule()
        self.schedule.pdf = self.schedule.generate_pdf(peak=peak, normal=normal, away=away, night=night)