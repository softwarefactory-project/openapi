import textwrap
import pytest

from sphinxcontrib.openapi import renderer


def textify(generator):
    return "\n".join(generator)


@pytest.fixture(scope="function")
def testrenderer():
    return renderer.HttpDomainRenderer("commonmark")
