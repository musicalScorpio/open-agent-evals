import unittest

from arlab.plugins import PLUGIN_GROUPS, PluginRegistry


class PluginRegistryTests(unittest.TestCase):
    def test_registers_and_creates_plugin(self) -> None:
        registry: PluginRegistry[dict[str, str]] = PluginRegistry(PLUGIN_GROUPS["evaluator"])
        registry.register("example", lambda config: {"id": config.get("id", "example")})

        self.assertEqual(registry.names(), ("example",))
        self.assertEqual(registry.create("example"), {"id": "example"})
        self.assertEqual(registry.create("example", {"id": "configured"}), {"id": "configured"})

    def test_rejects_duplicate_registration(self) -> None:
        registry: PluginRegistry[object] = PluginRegistry(PLUGIN_GROUPS["agent_adapter"])
        registry.register("example", lambda config: object())

        with self.assertRaises(ValueError):
            registry.register("example", lambda config: object())

    def test_reports_available_plugins(self) -> None:
        registry: PluginRegistry[object] = PluginRegistry(PLUGIN_GROUPS["evaluator"])
        registry.register("one", lambda config: object())

        with self.assertRaisesRegex(KeyError, "available: one"):
            registry.create("missing")


if __name__ == "__main__":
    unittest.main()
