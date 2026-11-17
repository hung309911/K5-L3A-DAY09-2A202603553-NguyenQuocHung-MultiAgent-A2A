"""Subprocess bootstrap used only by HTTP integration tests."""

import runpy
import sys

import common.llm
from tests.fake_llm import get_test_llm

common.llm.get_llm = get_test_llm
runpy.run_module(sys.argv[1], run_name="__main__")
