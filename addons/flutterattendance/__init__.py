from . import models
from . import controllers


def _seed_status_config_parameters(env):
    # A Boolean config_parameter field that's never been explicitly persisted
    # reads as unset, and res.config.settings' own save logic treats "unset"
    # as already equal to False - so the very first time someone unchecks
    # "Automatically Calculate Attendance Status" the write is silently
    # skipped. Seeding real values here (via set_param, which upserts safely)
    # avoids that ambiguous unset state from the start.
    ICP = env['ir.config_parameter'].sudo()
    if ICP.get_param('flutterattendance.status_auto_enabled') is False:
        ICP.set_param('flutterattendance.status_auto_enabled', 'True')
    if ICP.get_param('flutterattendance.status_default_code') is False:
        ICP.set_param('flutterattendance.status_default_code', 'present')
