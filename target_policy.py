"""Choose the requested window independently of the window revealed by hiding UI."""


def select_request_target(expected, recent, independent, usable, alive):
    if independent:
        return None
    candidate = expected if expected is not None else recent
    if candidate is not None and usable(candidate) and alive(candidate):
        return dict(candidate)
    if expected is not None:
        raise ValueError('That window is no longer available. Choose a window and try again; no action was sent.')
    raise ValueError('Choose the window you want to use, then try again; no action was sent.')


def independent_request(task, catalog, grid_active=False):
    from direct_commands import normalize_command
    from routing import normalize_launch_verb
    from catalog import launch_request
    from grid_commands import parse
    from window_commands import intent
    if task.startswith('/') or parse(task, grid_active) is not None:
        return True
    command = intent(task)
    if command and command['action'] == 'switch_window':
        return True
    name = launch_request(normalize_launch_verb(normalize_command(task)))
    if name:
        try:
            catalog.resolve(name)
            return True
        except ValueError:
            pass
    return False
