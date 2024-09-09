import os
import toml
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from settings import DATA_PATH

@dataclass
class Shower():
    name: str = "NormalShower"  # ... name of the end-use
    user_age: str = "work_ad"

    def __post_init__(self):
        #self.name = "Shower"
        self.diurnal_stats = toml.load(open(os.path.join(DATA_PATH, 'diurnal_distributions.toml'), 'r'))
        self.usage_stats = toml.load(open(os.path.join(DATA_PATH, 'end_uses', 'shower.toml'), 'r'))

    # def load_diurnal_statistics():
    #     # Load diurnal pattern statistics from .toml file
    #     diurnal_pattern_file = os.path.join(DATA_PATH, 'diurnal_distributions.toml')
    #     return toml.load(open(diurnal_pattern_file, 'r'))
    
    # def load_usage_statistics():
    #     # Load shower usage statistics from .toml file
    #     usage_stats_dir = os.path.join(DATA_PATH, 'end_uses', 'shower.toml')
    #     return toml.load(open(usage_stats_dir, 'r'))
    
    def frequency(self):
        # load shower frequency stats
        freq_stats = self.usage_stats['frequency']
        # select frequency distribution function from shower stats
        distribution = getattr(np.random, freq_stats['distribution'].lower())
        # assign 'n' and 'p' values for binomial distribution
        n = freq_stats['n']
        p = freq_stats['p'][self.user_age]

        return distribution(n, p)

    def duration_intensity(self):
        duration_stats = self.usage_stats['duration']
        # select frequency distribution function
        distribution = getattr(np.random, duration_stats['distribution'].lower())
        # parse time 'str' into Timedelta object and convert to minutes
        df = int(pd.Timedelta(duration_stats['df'][self.user_age]).total_seconds() / 60)
        # sample shower duration value using statistical distribution
        sampled_duration = distribution(df)
        duration = int(pd.Timedelta(minutes=sampled_duration).total_seconds()/60)
        
        intensity = self.usage_stats['subtype'][self.name]['intensity']
        return duration, intensity

    def simulate(self, consumption, users=None, ind_enduse=None, pattern_num=1, day_num=0):

        prob_usage = self.usage_probability().values

        for j, user in enumerate(users):
            freq = self.fct_frequency(age=user.age)
            prob_user = user.presence.values

            for i in range(freq):
                duration, intensity = self.fct_duration_intensity(age=user.age)

                prob_joint = normalize(prob_user * prob_usage)
                u = np.random.uniform()
                start = np.argmin(np.abs(np.cumsum(prob_joint) - u)) + int(pd.to_timedelta('1 day').total_seconds())*day_num
                end = start + duration
                consumption[start:end, j, ind_enduse, pattern_num] = intensity
                
        return consumption

shower = Shower()
freq = shower.frequency()
duration, intensity = shower.duration_intensity()