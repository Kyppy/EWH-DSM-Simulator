import os
import toml
import pandas as pd
import numpy as np
import random
from dataclasses import dataclass, field
from settings import DATA_PATH

@dataclass
class Shower():
    name: str = "NormalShower"  
    user_age: str = "work_ad"

    def __post_init__(self):
        #self.name = "Shower"
        self.diurnal_stats = toml.load(open(os.path.join(DATA_PATH, 'diurnal_distributions.toml'), 'r'))
        self.usage_stats = toml.load(open(os.path.join(DATA_PATH, 'end_uses', 'shower.toml'), 'r'))

    def frequency(self):
        # load shower frequency stats
        freq_stats = self.usage_stats['frequency']
        # select frequency distribution function from shower stats
        distribution = getattr(np.random, freq_stats['distribution'].lower())
        # assign 'n' and 'p' values for binomial distribution
        n = freq_stats['n']
        p = freq_stats['p'][self.user_age]

        return distribution(n, p)

    def duration_intensity(self, user_age):
        duration_stats = self.usage_stats['duration']
        # select frequency distribution function
        distribution = getattr(np.random, duration_stats['distribution'].lower())
        # parse time 'str' into Timedelta object and convert to minutes
        df = int(pd.Timedelta(duration_stats['df'][user_age]).total_seconds() / 60)
        # sample shower duration value using statistical distribution
        sampled_duration = distribution(df)
        duration = int(pd.Timedelta(minutes=sampled_duration).total_seconds()/60)
        
        intensity = self.usage_stats['subtype'][self.name]['intensity']
        return duration, intensity

    def simulate(self, user):
        duration, intensity = self.duration_intensity(user.age)
        #user.generate_pdf()
        cdf = np.cumsum(user.schedule.pdf)
        # randomly sample unique cdf value
        cdf_val = cdf[cdf==random.sample(list(set(cdf)), 1)[0]]
        if len(cdf_val) > 1:
            start = int(cdf_val.sample().index[0].total_seconds() / 60)
        else:
            start = int(cdf_val.index[0].total_seconds() / 60)
        #start = int(np.cumsum(user.schedule.pdf).sample().index[0].total_seconds() / 60)
        end = start + duration
        
        return start, end, intensity
