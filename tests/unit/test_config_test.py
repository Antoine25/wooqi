# -*- coding: utf-8 -*-

"""
Unit tests for wooqi.src.config_test
"""

import textwrap

import pytest

from wooqi.src.config_test import ConfigTest, MultiDict


@pytest.fixture(autouse=True)
def reset_multidict():
    """Reset MultiDict class-level state between tests."""
    MultiDict._keys_name_and_params = {}
    yield
    MultiDict._keys_name_and_params = {}


@pytest.fixture
def simple_ini(tmp_path):
    """Create a minimal valid ini file with one test step."""
    ini = tmp_path / "seq.ini"
    ini.write_text(
        textwrap.dedent("""\
        [test_foo]
        limit=42
        """)
    )
    return str(ini)


@pytest.fixture
def duplicate_sections_ini(tmp_path):
    """Create an ini file where the same step is called twice."""
    ini = tmp_path / "seq.ini"
    ini.write_text(
        textwrap.dedent("""\
        [test_foo]
        uut=a

        [test_foo]
        uut=b
        """)
    )
    return str(ini)


@pytest.fixture
def loop_ini(tmp_path):
    """Create an ini file with a loop."""
    ini = tmp_path / "seq.ini"
    ini.write_text(
        textwrap.dedent("""\
        [test_info]
        loop_tests=test_a|test_b
        loop_iter=3

        [test_a]

        [test_b]
        """)
    )
    return str(ini)


@pytest.fixture
def post_fail_ini(tmp_path):
    """Create an ini file with a valid post_fail."""
    ini = tmp_path / "seq.ini"
    ini.write_text(
        textwrap.dedent("""\
        [test_a]
        post_fail=test_b

        [test_b]
        """)
    )
    return str(ini)


# ---------------------------------------------------------------------------
# MultiDict
# ---------------------------------------------------------------------------


class TestMultiDict:
    def test_non_test_key_stored_as_is(self):
        d = MultiDict()
        d["general_info"] = {"key": "val"}
        assert "general_info" in d

    def test_first_occurrence_gets_suffix_zero(self):
        d = MultiDict()
        d["test_foo"] = {}
        assert "test_foo 0" in d

    def test_second_occurrence_gets_suffix_one(self):
        d = MultiDict()
        d["test_foo"] = {}
        d["test_foo"] = {}
        assert "test_foo 0" in d
        assert "test_foo 1" in d

    def test_explicit_suffix_accepted(self):
        d = MultiDict()
        d["test_foo-0"] = {}
        assert "test_foo 0" in d

    def test_too_many_dashes_raises(self):
        d = MultiDict()
        with pytest.raises(Exception, match="too much"):
            d["test_foo-0-1"] = {}

    def test_non_integer_suffix_raises(self):
        d = MultiDict()
        with pytest.raises(Exception, match="Value after - must be integer"):
            d["test_foo-bar"] = {}

    def test_duplicate_explicit_suffix_raises(self):
        d = MultiDict()
        d["test_foo-0"] = {}
        with pytest.raises(Exception, match="multiple call unclear"):
            d["test_foo-0"] = {}

    def test_action_prefix_also_tracked(self):
        d = MultiDict()
        d["action_bar"] = {}
        assert "action_bar 0" in d


# ---------------------------------------------------------------------------
# ConfigTest._get_parameter
# ---------------------------------------------------------------------------


class TestGetParameter:
    def test_integer_string(self):
        assert ConfigTest._get_parameter("42", None, None) == 42

    def test_float_string(self):
        assert ConfigTest._get_parameter("3.14", None, None) == pytest.approx(3.14)

    def test_list_string(self):
        assert ConfigTest._get_parameter("[1, 2, 3]", None, None) == [1, 2, 3]

    def test_default_returns_string(self):
        assert ConfigTest._get_parameter("Default", None, None) == "Default"

    def test_no_evaluate_returns_string(self):
        assert ConfigTest._get_parameter("42", None, None, evaluate=False) == "42"

    def test_dict_format_with_uut(self):
        assert ConfigTest._get_parameter("uut1:10|uut2:20", "uut1", None) == 10

    def test_dict_format_fallback_to_default(self):
        assert ConfigTest._get_parameter("uutX:10|Default:99", "unknown", None) == 99

    def test_dict_format_with_uut_and_uut2(self):
        result = ConfigTest._get_parameter("uut1-uut2:55|Default:0", "uut1", "uut2")
        assert result == 55

    def test_dict_format_no_uut_returns_dict(self):
        result = ConfigTest._get_parameter("a:1|b:2", None, None)
        assert result == {"a": 1, "b": 2}

    def test_dict_no_evaluate(self):
        result = ConfigTest._get_parameter("a:hello|b:world", None, None, evaluate=False)
        assert result == {"a": "hello", "b": "world"}

    def test_invalid_value_returns_none(self):
        # ast.literal_eval cannot parse arbitrary identifiers
        result = ConfigTest._get_parameter("not_a_literal", None, None)
        assert result is None


# ---------------------------------------------------------------------------
# ConfigTest._get_range
# ---------------------------------------------------------------------------


class TestGetRange:
    def test_two_args(self):
        assert ConfigTest._get_range("range(0,5)") == ["0", "1", "2", "3", "4"]

    def test_three_args_with_step(self):
        assert ConfigTest._get_range("range(0,6,2)") == ["0", "2", "4"]

    def test_single_element(self):
        assert ConfigTest._get_range("range(3,4)") == ["3"]


# ---------------------------------------------------------------------------
# ConfigTest initialisation
# ---------------------------------------------------------------------------


class TestConfigTestInit:
    def test_missing_file(self, tmp_path):
        cfg = ConfigTest(str(tmp_path / "nonexistent.ini"))
        assert cfg.config_file_exists is False

    def test_simple_file_loaded(self, simple_ini):
        cfg = ConfigTest(simple_ini)
        assert cfg.config_file_exists is True
        assert cfg.exist("test_foo")

    def test_unique_step_has_no_suffix(self, simple_ini):
        """A step that appears only once should NOT have -0 appended."""
        cfg = ConfigTest(simple_ini)
        assert cfg.exist("test_foo")
        assert not cfg.exist("test_foo-0")

    def test_duplicate_steps_renamed(self, duplicate_sections_ini):
        cfg = ConfigTest(duplicate_sections_ini)
        assert cfg.exist("test_foo-0")
        assert cfg.exist("test_foo-1")

    def test_loop_option_parsed(self, loop_ini):
        cfg = ConfigTest(loop_ini)
        result = cfg.loop_infos()
        assert result is not None
        loop_tests, loop_iter = result
        assert loop_tests == ["test_a", "test_b"]
        assert loop_iter == 3

    def test_loop_iter_applied_to_steps(self, loop_ini):
        cfg = ConfigTest(loop_ini)
        assert cfg.file_config["test_a"].get("wooqi_loop_iter") == 3
        assert cfg.file_config["test_b"].get("wooqi_loop_iter") == 3

    def test_invalid_loop_format_raises(self, tmp_path):
        ini = tmp_path / "bad_loop.ini"
        ini.write_text(
            textwrap.dedent("""\
            [test_info]
            loop_tests=test_a
            loop_iter=2

            [test_a]
            """)
        )
        with pytest.raises(Exception, match="loop option"):
            ConfigTest(str(ini))

    def test_loop_step_not_found_raises(self, tmp_path):
        ini = tmp_path / "bad_loop.ini"
        ini.write_text(
            textwrap.dedent("""\
            [test_info]
            loop_tests=test_a|test_missing
            loop_iter=2

            [test_a]
            """)
        )
        with pytest.raises(Exception, match="not found for loop option"):
            ConfigTest(str(ini))

    def test_invalid_post_fail_raises(self, tmp_path):
        ini = tmp_path / "bad_postfail.ini"
        ini.write_text(
            textwrap.dedent("""\
            [test_a]
            post_fail=test_nonexistent
            """)
        )
        with pytest.raises(Exception, match="post_fail"):
            ConfigTest(str(ini))

    def test_post_fail_next_step_is_valid(self, tmp_path):
        ini = tmp_path / "seq.ini"
        ini.write_text(
            textwrap.dedent("""\
            [test_a]
            post_fail=next_step
            """)
        )
        cfg = ConfigTest(str(ini))
        assert cfg.post_fail("test_a") == "next_step"


# ---------------------------------------------------------------------------
# ConfigTest getter methods
# ---------------------------------------------------------------------------


class TestConfigTestGetters:
    def test_exist_true(self, simple_ini):
        cfg = ConfigTest(simple_ini)
        assert cfg.exist("test_foo") is True

    def test_exist_false(self, simple_ini):
        cfg = ConfigTest(simple_ini)
        assert cfg.exist("test_missing") is False

    def test_order(self, simple_ini):
        cfg = ConfigTest(simple_ini)
        assert cfg.order("test_foo") == 1

    def test_uut_list(self, tmp_path):
        ini = tmp_path / "seq.ini"
        ini.write_text("[test_foo]\nuut=a|b|c\n")
        cfg = ConfigTest(str(ini))
        assert cfg.uut("test_foo") == ["a", "b", "c"]

    def test_uut_range(self, tmp_path):
        ini = tmp_path / "seq.ini"
        ini.write_text("[test_foo]\nuut=range(0,3)\n")
        cfg = ConfigTest(str(ini))
        assert cfg.uut("test_foo") == ["0", "1", "2"]

    def test_uut_none_when_absent(self, simple_ini):
        cfg = ConfigTest(simple_ini)
        assert cfg.uut("test_foo") is None

    def test_reruns(self, tmp_path):
        ini = tmp_path / "seq.ini"
        ini.write_text("[test_foo]\nreruns=3\n")
        cfg = ConfigTest(str(ini))
        assert cfg.reruns("test_foo") == 3

    def test_reruns_none_when_absent(self, simple_ini):
        cfg = ConfigTest(simple_ini)
        assert cfg.reruns("test_foo") is None

    def test_timeout(self, tmp_path):
        ini = tmp_path / "seq.ini"
        ini.write_text("[test_foo]\ntimeout=30\n")
        cfg = ConfigTest(str(ini))
        assert cfg.timeout("test_foo") == 30

    def test_timeout_none_when_absent(self, simple_ini):
        cfg = ConfigTest(simple_ini)
        assert cfg.timeout("test_foo") is None

    def test_post_fail(self, post_fail_ini):
        cfg = ConfigTest(post_fail_ini)
        assert cfg.post_fail("test_a") == "test_b"

    def test_post_fail_none_when_absent(self, simple_ini):
        cfg = ConfigTest(simple_ini)
        assert cfg.post_fail("test_foo") is None

    def test_limit(self, tmp_path):
        ini = tmp_path / "seq.ini"
        ini.write_text("[test_foo]\nlimit=100\n")
        cfg = ConfigTest(str(ini))
        assert cfg.limit("test_foo", None, None) == 100

    def test_limit_none_when_absent(self, tmp_path):
        ini = tmp_path / "seq.ini"
        ini.write_text("[test_foo]\n")
        cfg = ConfigTest(str(ini))
        assert cfg.limit("test_foo", None, None) is None

    def test_comparator_default(self, simple_ini):
        cfg = ConfigTest(simple_ini)
        assert cfg.comparator("test_foo", None, None) == "=="

    def test_comparator_custom(self, tmp_path):
        ini = tmp_path / "seq.ini"
        ini.write_text("[test_foo]\ncomparator=>=\n")
        cfg = ConfigTest(str(ini))
        assert cfg.comparator("test_foo", None, None) == ">="

    def test_loop_infos_none_when_absent(self, simple_ini):
        cfg = ConfigTest(simple_ini)
        assert cfg.loop_infos() is None
