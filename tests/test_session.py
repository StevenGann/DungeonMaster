"""Tests for Session and SessionManager."""

from dungeonmaster.core.session import Session, SessionManager


def test_session_add_turn():
    s = Session(session_id="u1")
    s.add_turn("user", "I attack")
    s.add_turn("assistant", "You hit!")
    assert len(s.turns) == 2
    assert s.turns[0].content == "I attack"


def test_session_get_recent():
    s = Session(session_id="u1")
    for i in range(25):
        s.add_turn("user", f"m{i}")
        s.add_turn("assistant", f"r{i}")
    recent = s.get_recent_turns(max_turns=10)
    assert len(recent) == 10
    # Last 10 turns are m20,r20,...,m24,r24
    assert recent[0].content == "m20"


def test_session_to_messages():
    s = Session(session_id="u1")
    s.add_turn("user", "hello")
    s.add_turn("assistant", "hi")
    msgs = s.to_messages(max_turns=5)
    assert msgs == [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]


def test_session_manager_get_or_create():
    mgr = SessionManager()
    s1 = mgr.get_or_create("u1")
    s2 = mgr.get_or_create("u1")
    assert s1 is s2
    s3 = mgr.get_or_create("u2")
    assert s3 is not s1
    assert mgr.get("u3") is None
    assert mgr.get("u1") is s1
