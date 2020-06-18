import os
import types


def load_config(root_path, filename):
    """This method was heavily borrowed from the flask config.py file's from_pyfile method.
    It reads a file containing python constants and loads it into a dictionary.

    :param root_path: the path leading to the config file
    :param filename: the filename of the config relative to the
                     root path.
    """
    filename = os.path.join(root_path, filename)
    d = types.ModuleType("config")
    d.__file__ = filename
    return_dict = {}
    try:
        with open(filename, mode="rb") as config_file:
            exec(compile(config_file.read(), filename, "exec"), d.__dict__)
        for config_key in d.__dict__:
            if str(config_key).startswith('__') == False:
                return_dict[config_key] = d.__dict__[config_key]
    except OSError as e:
        e.strerror = f"Unable to load configuration file ({e.strerror})"
        raise
    return return_dict

if __name__ == "__main__":
    root_path = '/git/ingest-ui/src/ingest-api/instance'
    filename = 'app.cfg'
    load_config(root_path, filename)
