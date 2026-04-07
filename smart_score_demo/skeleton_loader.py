import ast
import copy
from pathlib import Path


def load_demo_skeleton(demo_py_path: Path) -> dict:
    """Read demo.py and extract the bid_demo_data dict defined in main()."""
    source = demo_py_path.read_text(encoding="utf-8")
    module = ast.parse(source)

    for node in module.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "main":
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "bid_demo_data" for target in stmt.targets):
                continue
            data = ast.literal_eval(stmt.value)
            return copy.deepcopy(data)

    raise ValueError(f"Unable to find bid_demo_data in {demo_py_path}")
