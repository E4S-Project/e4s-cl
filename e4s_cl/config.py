import yaml

confxGlobal = {'container directory': 'CONTAINER_DIR'}

class Configuration:
    updated_globals = dict()

    def __init__(self, confFile):
        with open(confFile) as f:
            self.data = yaml.safe_load(f)
        for key in self.data.keys():
            global_key = confxGlobal[key]
            self.updated_globals.update({confxGlobal[key]: self.data[key]})
