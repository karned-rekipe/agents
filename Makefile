.PHONY: run-pydantic-ai run-langchain run-langgraph

run-pydantic-ai:
	cd pydantic_ai && uv run chainlit run main.py

run-langchain:
	cd langchain && uv run python main.py

run-langgraph:
	cd langgraph && uv run python main.py

