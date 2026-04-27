"""Bad frames must always raise pydantic ValidationError, never crash anything else."""

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from canastra.web.messages import ClientEnvelope


@given(s=st.text(max_size=200))
@settings(max_examples=200)
def test_random_string_either_validates_or_validation_errors(s):
    """No SystemError, no IndexError, no panic — just clean ValidationError or success."""
    try:
        parsed = json.loads(s)
    except (json.JSONDecodeError, ValueError):
        return  # not a JSON; client receive loop catches separately
    try:
        ClientEnvelope.model_validate(parsed)
    except ValidationError:
        pass
    except Exception as exc:
        pytest.fail(f"Unexpected exception type: {type(exc).__name__}: {exc}")


@given(payload=st.dictionaries(st.text(max_size=10), st.integers() | st.text(max_size=10)))
@settings(max_examples=200)
def test_random_dict_clean_failure(payload):
    try:
        ClientEnvelope.model_validate(payload)
    except ValidationError:
        pass
    except Exception as exc:
        pytest.fail(f"Unexpected exception type: {type(exc).__name__}: {exc}")
