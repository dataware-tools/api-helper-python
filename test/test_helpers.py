#!/usr/bin/env python


def test_escape_string():
    """Test for escape_string."""
    from dataware_tools_api_helper.helpers import escape_string

    assert escape_string('record_id:abc name:def', kind='filtering') == 'record_id:abc name:def'
    assert escape_string('abc-def1234;[+"', kind='id') == 'abc-def1234'
    assert escape_string('/rosbag/topic@#$%', kind='key') == '/rosbag/topic@'
    assert escape_string('/path/to/file.ext', kind='path') == '/path/to/file.ext'
    assert escape_string('38123[[F9I{)(UFOIU#Y&(!', kind='uuid') == '38123F9IUFOIUY'
