import sys
from pathlib import Path

from swe_struct.agent.limits import Limits
from swe_struct.agent.loop import run_agent
from swe_struct.backends.openai_compat import OpenAICompatBackend
from swe_struct.core.types import Message, RepoContext
from swe_struct.tools.registry import ToolRegistry
from swe_struct.tools.submit import SubmitTool


def main(model: str = "gemma4:31b-cloud") -> None:
    backend = OpenAICompatBackend("http://localhost:11434/v1", model)
    outcome = run_agent(
        backend=backend,
        registry=ToolRegistry([SubmitTool()]),
        ctx=RepoContext(root=Path(".")),
        messages=[
            Message(
                role="user",
                content="The bug is in parser.py, function parse_config. Report it with the submit tool.",
            )
        ],
        tool_names=["submit"],
        limits=Limits(max_steps=3),
    )
    print(outcome.model_dump_json(indent=2))


if __name__ == "__main__":
    main(*sys.argv[1:])