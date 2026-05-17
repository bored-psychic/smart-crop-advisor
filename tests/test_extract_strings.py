"""Tests for the JSX unwrapped-string extractor."""
from pathlib import Path
from scripts.i18n.extract_strings import find_unwrapped_strings


def _run(src: str):
    return [m.text for m in find_unwrapped_strings(src, filename="x.jsx")]


def test_finds_jsx_text_children():
    src = """function X(){ return <div>Hello world</div>; }"""
    assert "Hello world" in _run(src)


def test_ignores_t_wrapped():
    src = """function X({t}){ return <div>{t('Hello')}</div>; }"""
    assert _run(src) == []


def test_finds_placeholder_attribute():
    src = """function X(){ return <input placeholder="Type here" />; }"""
    assert "Type here" in _run(src)


def test_finds_aria_label_and_title():
    src = """function X(){ return <button aria-label="Close" title="Dismiss" />; }"""
    out = _run(src)
    assert "Close" in out and "Dismiss" in out


def test_ignores_classname_and_style_and_id():
    src = """function X(){ return <div className="btn primary" id="root" style={{color:'red'}} />; }"""
    assert _run(src) == []


def test_ignores_pure_numbers_and_punctuation():
    src = """function X(){ return <span>42</span>; }"""
    assert _run(src) == []


def test_ignores_existing_t_call_attribute():
    src = """function X({t}){ return <input placeholder={t('Type')} />; }"""
    assert _run(src) == []


def test_ignores_url_like_strings():
    src = """const u = "/api/crop"; const v = "https://x.com";"""
    assert _run(src) == []


def test_ignores_console_calls():
    src = """function X(){ console.log("debug only"); }"""
    assert _run(src) == []
