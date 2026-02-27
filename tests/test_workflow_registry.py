import unittest

from jbom.workflows.registry import register, get, clear


class TestWorkflowRegistry(unittest.TestCase):
    def tearDown(self):
        clear()

    def test_register_and_get(self):
        def f(x):
            return x + 1

        register("add1", f)
        self.assertIs(get("add1"), f)
        self.assertEqual(get("add1")(1), 2)

    def test_missing_raises(self):
        with self.assertRaises(KeyError):
            get("nope")


if __name__ == "__main__":
    unittest.main()
