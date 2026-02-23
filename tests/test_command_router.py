from app.core.command_router import CommandRouter


def test_start_and_stop_routes():
    router = CommandRouter()
    assert router.route('Assistant start safe navigation') == 'START'
    assert router.route('Assistant stop safe navigation') == 'STOP'


def test_query_routes():
    router = CommandRouter()
    assert router.route("What's ahead?") == 'WHAT_AHEAD'
    assert router.route('Describe the scene') == 'DESCRIBE_SCENE'


def test_help_route():
    router = CommandRouter()
    assert router.route("Help") == "HELP"
    assert router.route("What can you do") == "HELP"


def test_strict_stop_phrase():
    router = CommandRouter()
    assert router.route("Stop navigation") == "UNKNOWN"
    assert router.route("Stop") == "UNKNOWN"
