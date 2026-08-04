import pytest
from pydantic import ValidationError

from backend.schemas import (
    MAX_CONTRACT_CHARS,
    MAX_MATCH_TOTAL_CHARS,
    MAX_MEETING_CHARS,
    MAX_REPORT_TOTAL_CHARS,
    ContractRequest,
    MatchRequest,
    MeetingRequest,
    ProfileData,
    ReportRequest,
)


def test_meeting_input_length_limit():
    with pytest.raises(ValidationError):
        MeetingRequest(text="a" * (MAX_MEETING_CHARS + 1))


def test_contract_input_length_limit():
    with pytest.raises(ValidationError):
        ContractRequest(text="a" * (MAX_CONTRACT_CHARS + 1))


def test_match_total_length_limit():
    half = MAX_MATCH_TOTAL_CHARS // 2 + 1
    with pytest.raises(ValidationError):
        MatchRequest(profile=ProfileData(), offer="a" * half, need="b" * half)


def test_report_total_length_limit():
    with pytest.raises(ValidationError):
        ReportRequest(results={"报告": "a" * (MAX_REPORT_TOTAL_CHARS + 1)})
