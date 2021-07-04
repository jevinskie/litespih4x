import litejtag_ext
from litejtag_ext.hello import JTAGHello


def test_version():
    assert litejtag_ext.__version__ == '0.1.0'
