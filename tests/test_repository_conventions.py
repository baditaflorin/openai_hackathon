from __future__ import annotations

import importlib
import os
import pkgutil
import sys
import tempfile
import unittest


def reset_clipmato_modules() -> None:
    for name in list(sys.modules):
        if name == "clipmato" or name.startswith("clipmato."):
            sys.modules.pop(name)


class RepositoryConventionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        os.environ["CLIPMATO_DATA_DIR"] = self.tempdir.name
        reset_clipmato_modules()

    def test_router_discovery_matches_router_modules(self) -> None:
        routers_pkg = importlib.import_module("clipmato.routers")

        expected = []
        for _finder, module_name, _ispkg in pkgutil.iter_modules(routers_pkg.__path__):
            if module_name.startswith("_"):
                continue
            module = importlib.import_module(f"clipmato.routers.{module_name}")
            if hasattr(module, "router"):
                expected.append(module.router)

        self.assertEqual({id(router) for router in routers_pkg.list_routers()}, {id(router) for router in expected})

    def test_agent_discovery_matches_agent_modules(self) -> None:
        agents_pkg = importlib.import_module("clipmato.agents")

        expected = {}
        for _finder, module_name, _ispkg in pkgutil.iter_modules(agents_pkg.__path__):
            if module_name.startswith("_"):
                continue
            module = importlib.import_module(f"clipmato.agents.{module_name}")
            for attr in dir(module):
                if attr.endswith("_agent"):
                    agent = getattr(module, attr)
                    expected[agent.name] = agent

        self.assertEqual(set(agents_pkg.list_agents()), set(expected))

    def test_step_exports_follow_public_callable_convention(self) -> None:
        steps_pkg = importlib.import_module("clipmato.steps")

        expected = set()
        for _finder, module_name, _ispkg in pkgutil.iter_modules(steps_pkg.__path__):
            if module_name.startswith("_") or module_name == "step_utils":
                continue
            module = importlib.import_module(f"clipmato.steps.{module_name}")
            for attr in dir(module):
                if attr.startswith("_"):
                    continue
                obj = getattr(module, attr)
                if callable(obj) and getattr(obj, "__module__", None) == module.__name__:
                    expected.add(attr)

        self.assertTrue(expected.issubset(set(steps_pkg.__all__)))
        for name in expected:
            self.assertTrue(callable(getattr(steps_pkg, name)))


if __name__ == "__main__":
    unittest.main()
