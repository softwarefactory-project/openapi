"""OpenAPI spec renderer."""

import functools
import inspect

import m2r
from sphinx.util import logging


logger = logging.getLogger(__name__)


def render(spec, markup="commonmark"):
    """The one func to rule them all."""
    return nodes


missing = object()


def getin(sequence_or_mapping, path, default=missing):
    rv = sequence_or_mapping

    try:
        for part in path:
            rv = rv[part]
    except (IndexError, KeyError, LookupError):
        if default is not missing:
            return default
        raise

    return rv


def indented(generator, indent=4):
    for item in generator:
        yield " " * indent + item


def _yield_from_generators(generatorfn):
    @functools.wraps(generatorfn)
    def _wrapper(*args, **kwargs):
        for subgenerator in generatorfn(*args, **kwargs):
            if inspect.isgenerator(subgenerator):
                for item in subgenerator:
                    yield item
            else:
                yield subgenerator

    return _wrapper


def _from_restructuredtext_markup(generatorfn):
    pass


class HttpDomainRenderer(object):
    """Render OpenAPI v3 using `sphinxcontrib-httpdomain` extension."""

    # render(...)
    #   render_paths(...)
    #     render_operation(...)
    #       render_parameters(...)
    #         render_parameter(...)
    #       render_responses(...)
    #         render_response(...)

    _markup_converters = {"commonmark": m2r.convert, "restructuredtext": lambda x: x}

    def __init__(self, markup, request_parameters_order=None):
        self._convert_markup = self._markup_converters[markup]
        self._request_parameters_order = ["header", "path", "query", "cookie"]

    @_yield_from_generators
    def render(self, node):
        """Spec render entry point."""
        yield self.render_paths(node)

    @_yield_from_generators
    def render_paths(self, node):
        """Render OAS paths item."""

        for endpoint, pathitem in getin(node, ["paths"], {}).items():
            for method, operation in pathitem.items():
                operation.setdefault("parameters", [])
                parameters = [
                    parameter
                    for parameter in pathitem.get("parameters", [])
                    if (parameter["name"], parameter["in"])
                    not in [
                        (op_parameter["name"], op_parameter["in"])
                        for op_parameter in operation.get("parameters", [])
                    ]
                ]
                operation["parameters"] += parameters

                yield self.render_operation(endpoint, method, operation)
                yield ""

    @_yield_from_generators
    def render_operation(self, endpoint, method, operation):
        """Render OAS operation item."""

        yield ".. http:%s:: %s" % (method, endpoint)

        if operation.get("deprecated"):
            yield "    :deprecated:"

        yield ""

        if operation.get("summary"):
            yield "    **%s**" % operation["summary"]
            yield ""

        if operation.get("description"):
            yield indented(
                self._convert_markup(operation["description"]).strip().splitlines()
            )
            yield ""

        yield indented(self.render_parameters(operation.get("parameters", [])))
        yield indented(self.render_responses(operation["responses"]))

    @_yield_from_generators
    def render_parameters(self, parameters):
        """Render OAS operation's parameters."""

        for parameter in sorted(
            parameters,
            key=lambda p: self._request_parameters_order.index(p["in"].lower()),
        ):
            yield self.render_parameter(parameter)

    @_yield_from_generators
    def render_parameter(self, parameter):
        """Render OAS operation's parameter."""

        kinds = {"path": "param", "query": "queryparam", "header": "reqheader"}
        markers = []
        schema = parameter.get("schema", {})

        if parameter["in"] not in kinds:
            logger.warning(
                "OpenAPI spec contains parameter '%s' (in: '%s') that cannot "
                "be rendererd.",
                parameter["name"],
                parameter["in"],
            )
            return

        if schema.get("type"):
            type_ = schema.get("type")
            if schema.get("format"):
                type_ = "%s:%s" % (type_, schema.get("format"))
            markers.append(type_)

        if parameter.get("required"):
            markers.append("required")

        if parameter.get("deprecated"):
            markers.append("deprecated")

        yield ":%s %s:" % (kinds[parameter["in"]], parameter["name"])

        if parameter.get("description"):
            yield indented(
                self._convert_markup(parameter["description"]).strip().splitlines()
            )

        if markers:
            yield ":%s %s: %s" % (
                "%stype" % kinds[parameter["in"]],
                parameter["name"],
                ", ".join(markers),
            )

    @_yield_from_generators
    def render_responses(self, responses):
        """Render OAS operation's responses."""

        for status_code, response in responses.items():
            yield self.render_response(status_code, response)

    @_yield_from_generators
    def render_response(self, status_code, response):
        """Render OAS operation's response."""

        yield ":statuscode %s:" % status_code
        yield indented(
            self._convert_markup(response["description"]).strip().splitlines()
        )
        # yield ""
        # yield ":responseheader X-Trace-Id: What the Fuck?"
