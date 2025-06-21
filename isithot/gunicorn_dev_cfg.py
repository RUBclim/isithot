import os

bind = '0.0.0.0:5005'
log_level = 'debug'
workers = 1
reload = True
template_dir = 'web/isithot/templates'
extra_files = [os.path.join(template_dir, f) for f in os.listdir(template_dir)]
reload_extra_files = extra_files
