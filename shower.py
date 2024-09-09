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
        start = int(user.generate_pdf().sample().index[0].total_seconds() / 60)
        end = start + duration
        
        return start, end, intensity

# shower = Shower()
# freq = shower.frequency()
# duration, intensity = shower.duration_intensity()