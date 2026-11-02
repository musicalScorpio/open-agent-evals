import unittest

from arlab.agents import AgentDefinition


class AgentDefinitionTests(unittest.TestCase):
    def test_builds_from_portable_mapping(self) -> None:
        definition = AgentDefinition.from_mapping(
            {
                "id": "example.agent",
                "version": "1.0",
                "description": "Example",
                "runtime": {"adapter": "example", "mode": "in_process"},
                "model": {
                    "provider": "ollama",
                    "name": "example:latest",
                    "license": "Apache-2.0",
                    "options": {"temperature": 0},
                },
                "capabilities": {"tool_use": True},
                "permissions": {"default": "deny"},
                "limits": {"max_turns": 1},
            }
        )

        self.assertEqual(definition.adapter, "example")
        self.assertEqual(definition.model.provider, "ollama")
        self.assertTrue(definition.capabilities.tool_use)
        self.assertFalse(definition.capabilities.multi_turn)

    def test_requires_identity(self) -> None:
        with self.assertRaises(ValueError):
            AgentDefinition.from_mapping(
                {
                    "id": "",
                    "version": "1.0",
                    "runtime": {"adapter": "example"},
                    "model": {"provider": "ollama", "name": "example"},
                }
            )


if __name__ == "__main__":
    unittest.main()

