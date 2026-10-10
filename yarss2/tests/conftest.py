import importlib.util

collect_ignore = []

# PyGObject is only installed with the optional `gui` dependency group.
if importlib.util.find_spec("gi") is None:
    collect_ignore += [
        "test_dialog_cookies.py",
        "test_dialog_rssfeed.py",
        "test_dialog_subscription.py",
        "test_gtkui.py",
    ]
