import pytest


# pytest-twisted runs plain test functions inside its reactor greenlet,
# which leaves the reactor running for the trial test cases collected after them.
# The atoma tests are synchronous upstream tests, so they are called directly instead.
@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    testargs = {arg: pyfuncitem.funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames}
    pyfuncitem.obj(**testargs)
    return True
