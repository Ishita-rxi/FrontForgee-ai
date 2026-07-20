"""Shared behaviour for every agent in the pipeline."""

from utils.llm_client import LLMClient


class BaseAgent:
    name = "Base Agent"

    def __init__(self, llm: LLMClient):
        self.llm = llm
