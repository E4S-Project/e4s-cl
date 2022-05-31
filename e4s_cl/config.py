import yaml

class Configuration:
    def __init__(self, confFile):
        with open(confFile) as f:
            self.data = yaml.safe_load(f)
