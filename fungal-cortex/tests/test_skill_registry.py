"""Tests for skill_registry module — 209 skill management with dependency resolution."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.core.skill_registry import SkillMeta, SkillRegistry


class TestSkillMeta:
    def test_creation_defaults(self):
        meta = SkillMeta(name="test-skill")
        assert meta.name == "test-skill"
        assert meta.version == "1.0.0"
        assert meta.description == ""
        assert meta.enabled is True
        assert meta.call_count == 0
        assert meta.dependencies == []
        assert meta.keywords == []

    def test_creation_full(self):
        meta = SkillMeta(
            name="alpha-ear",
            version="2.1.0",
            description="Earnings analysis skill",
            module="alphaear-stock",
            category="alphaear",
            keywords=["earnings", "analysis"],
            dependencies=["data-provider"],
            enabled=False,
        )
        assert meta.module == "alphaear-stock"
        assert meta.category == "alphaear"
        assert meta.dependencies == ["data-provider"]
        assert meta.enabled is False

    def test_to_dict(self):
        meta = SkillMeta(
            name="test-skill",
            version="1.0.0",
            description="A test skill",
            module="test-module",
            category="test-category",
            keywords=["test", "unit"],
            dependencies=["dep1"],
        )
        d = meta.to_dict()
        assert d["name"] == "test-skill"
        assert d["version"] == "1.0.0"
        assert d["description"] == "A test skill"
        assert d["module"] == "test-module"
        assert d["category"] == "test-category"
        assert d["keywords"] == ["test", "unit"]
        assert d["dependencies"] == ["dep1"]
        assert d["enabled"] is True
        assert d["call_count"] == 0


class TestSkillRegistry:
    @pytest.fixture
    def reg(self):
        return SkillRegistry()

    @pytest.fixture
    def skill_a(self):
        return SkillMeta(name="skill-a", module="mod1", category="core", keywords=["kw1", "kw2"])

    @pytest.fixture
    def skill_b(self):
        return SkillMeta(name="skill-b", module="mod1", category="core", keywords=["kw2", "kw3"], dependencies=["skill-a"])

    @pytest.fixture
    def skill_c(self):
        return SkillMeta(name="skill-c", module="mod2", category="agent-plugin", keywords=["kw3"])

    def test_register_new_skill(self, reg, skill_a):
        assert reg.register(skill_a) is True
        assert reg.count == 1

    def test_register_duplicate_fails(self, reg, skill_a):
        reg.register(skill_a)
        assert reg.register(skill_a) is False
        assert reg.count == 1

    def test_unregister_existing(self, reg, skill_a):
        reg.register(skill_a)
        assert reg.unregister("skill-a") is True
        assert reg.count == 0

    def test_unregister_with_dependents_fails(self, reg, skill_a, skill_b):
        reg.register(skill_a)
        reg.register(skill_b)
        assert reg.unregister("skill-a") is False  # skill-b depends on skill-a

    def test_unregister_nonexistent(self, reg):
        assert reg.unregister("nonexistent") is False

    def test_get_existing(self, reg, skill_a):
        reg.register(skill_a)
        assert reg.get("skill-a") is skill_a

    def test_get_nonexistent(self, reg):
        assert reg.get("nonexistent") is None

    def test_list_all(self, reg, skill_a, skill_b):
        reg.register(skill_a)
        reg.register(skill_b)
        assert len(reg.list_all()) == 2

    def test_search_by_name(self, reg, skill_a, skill_c):
        reg.register(skill_a)
        reg.register(skill_c)
        results = reg.search("skill-a")
        assert len(results) == 1
        assert results[0].name == "skill-a"

    def test_search_by_description(self, reg):
        meta = SkillMeta(name="desc-skill", description="Alpha ear analysis engine")
        reg.register(meta)
        results = reg.search("alpha ear")
        assert len(results) == 1

    def test_search_by_keyword(self, reg, skill_a):
        reg.register(skill_a)
        results = reg.search("kw1")
        assert len(results) == 1

    def test_search_case_insensitive(self, reg, skill_a):
        reg.register(skill_a)
        results = reg.search("KW1")
        assert len(results) == 1

    def test_by_module(self, reg, skill_a, skill_b, skill_c):
        reg.register(skill_a)
        reg.register(skill_b)
        reg.register(skill_c)
        mod1 = reg.by_module("mod1")
        assert len(mod1) == 2

    def test_by_module_empty(self, reg):
        assert reg.by_module("nonexistent") == []

    def test_by_category(self, reg, skill_a, skill_c):
        reg.register(skill_a)
        reg.register(skill_c)
        assert len(reg.by_category("core")) == 1
        assert len(reg.by_category("agent-plugin")) == 1

    def test_by_category_empty(self, reg):
        assert reg.by_category("nonexistent") == []

    def test_resolve_dependencies_simple(self, reg, skill_a, skill_b):
        reg.register(skill_a)
        reg.register(skill_b)
        order = reg.resolve_dependencies("skill-b")
        assert order[0] == "skill-a"
        assert order[1] == "skill-b"

    def test_resolve_dependencies_no_deps(self, reg, skill_a):
        reg.register(skill_a)
        order = reg.resolve_dependencies("skill-a")
        assert order == ["skill-a"]

    def test_resolve_dependencies_cyclic(self, reg):
        """Skills with circular dependencies should raise ValueError."""
        a = SkillMeta(name="a", dependencies=["b"])
        b = SkillMeta(name="b", dependencies=["a"])
        reg.register(a)
        reg.register(b)
        with pytest.raises(ValueError, match="Circular"):
            reg.resolve_dependencies("a")

    def test_get_load_order(self, reg, skill_a, skill_b, skill_c):
        reg.register(skill_a)
        reg.register(skill_b)
        reg.register(skill_c)
        order = reg.get_load_order()
        assert len(order) == 3
        # skill-a must come before skill-b (dependency)
        assert order.index("skill-a") < order.index("skill-b")

    def test_get_load_order_circular(self, reg):
        a = SkillMeta(name="x", dependencies=["y"])
        b = SkillMeta(name="y", dependencies=["x"])
        reg.register(a)
        reg.register(b)
        with pytest.raises(ValueError, match="Circular"):
            reg.get_load_order()

    def test_count(self, reg, skill_a, skill_b):
        assert reg.count == 0
        reg.register(skill_a)
        assert reg.count == 1
        reg.register(skill_b)
        assert reg.count == 2

    def test_enabled_count(self, reg, skill_a, skill_b):
        skill_b.enabled = False
        reg.register(skill_a)
        reg.register(skill_b)
        assert reg.enabled_count == 1

    def test_record_call(self, reg, skill_a):
        reg.register(skill_a)
        reg.record_call("skill-a")
        assert skill_a.call_count == 1
        assert skill_a.last_called > 0

    def test_record_call_nonexistent(self, reg):
        reg.record_call("nonexistent")  # Should not raise

    def test_import_from_quantmind(self, reg):
        """Test bulk import from a temp directory with SKILL.md files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "alphaear-stock"
            skill_dir.mkdir(parents=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text("""# alpha-ear-stock
description: Stock market ear analysis
version: 2.0.0
tags: ear, stock, market
""")
            imported = reg.import_from_quantmind(Path(tmpdir))
            assert imported >= 1
            skill = reg.get("alpha-ear-stock")
            assert skill is not None

    def test_parse_skill_file_with_all_fields(self, reg):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "adaptive-engine"
            skill_dir.mkdir(parents=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text("""# adaptive-engine
description: The core adaptive engine
version: 2.0.0
keywords: engine, adaptive, core
some other content here
""")
            imported = reg.import_from_quantmind(Path(tmpdir))
            assert imported >= 1
            skill = reg.get("adaptive-engine")
            assert skill is not None
            assert skill.keywords == ["engine", "adaptive", "core"]

    def test_classify_agent_plugin(self, reg):
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir) / "agent-plugins" / "china-dcf"
            plugins_dir.mkdir(parents=True)
            (plugins_dir / "SKILL.md").write_text("# china-dcf")
            imported = reg.import_from_quantmind(Path(tmpdir))
            assert imported >= 1
            skill = reg.get("china-dcf")
            assert skill.category == "agent-plugin"

    def test_classify_vertical_plugin(self, reg):
        with tempfile.TemporaryDirectory() as tmpdir:
            vp_dir = Path(tmpdir) / "vertical-plugins" / "china-nav-tieout"
            vp_dir.mkdir(parents=True)
            (vp_dir / "SKILL.md").write_text("# china-nav-tieout")
            imported = reg.import_from_quantmind(Path(tmpdir))
            assert imported >= 1
            skill = reg.get("china-nav-tieout")
            assert skill.category == "vertical-plugin"

    def test_classify_alphaear(self, reg):
        with tempfile.TemporaryDirectory() as tmpdir:
            ae_dir = Path(tmpdir) / "alphaear-stock"
            ae_dir.mkdir(parents=True)
            (ae_dir / "SKILL.md").write_text("# alphaear-stock")
            imported = reg.import_from_quantmind(Path(tmpdir))
            assert imported >= 1
            skill = reg.get("alphaear-stock")
            assert skill.category == "alphaear"

    def test_classify_data_pack(self, reg):
        with tempfile.TemporaryDirectory() as tmpdir:
            dp_dir = Path(tmpdir) / "data-pack" / "a-stock-data"
            dp_dir.mkdir(parents=True)
            (dp_dir / "SKILL.md").write_text("# a-stock-data")
            imported = reg.import_from_quantmind(Path(tmpdir))
            assert imported >= 1

    def test_classify_platform(self, reg):
        with tempfile.TemporaryDirectory() as tmpdir:
            pf_dir = Path(tmpdir) / "l6-cognition-platform"
            pf_dir.mkdir(parents=True)
            (pf_dir / "SKILL.md").write_text("# l6-cognition-platform")
            imported = reg.import_from_quantmind(Path(tmpdir))
            assert imported >= 1
            skill = reg.get("l6-cognition-platform")
            assert skill.category == "platform"

    def test_classify_engine(self, reg):
        with tempfile.TemporaryDirectory() as tmpdir:
            eng_dir = Path(tmpdir) / "adaptive-engine"
            eng_dir.mkdir(parents=True)
            (eng_dir / "SKILL.md").write_text("# adaptive-engine")
            imported = reg.import_from_quantmind(Path(tmpdir))
            assert imported >= 1
            skill = reg.get("adaptive-engine")
            assert skill.category == "engine"

    def test_parse_skill_file_error(self, reg):
        """Test that a malformed file is silently skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_dir = Path(tmpdir) / "bad-skill"
            bad_dir.mkdir(parents=True)
            # Write binary content that can't be read as utf-8 text
            (bad_dir / "SKILL.md").write_bytes(b"\xff\xfe\x00\x01")
            imported = reg.import_from_quantmind(Path(tmpdir))
            assert imported == 0

    def test_search_multiple_matches(self, reg):
        reg.register(SkillMeta(name="alpha-ear", keywords=["earnings"]))
        reg.register(SkillMeta(name="alpha-stock", keywords=["stock"]))
        reg.register(SkillMeta(name="beta-ear", description="earnings analysis tool"))
        results = reg.search("ear")
        assert len(results) >= 1  # At least one should match

    def test_record_call_multiple(self, reg, skill_a):
        reg.register(skill_a)
        reg.record_call("skill-a")
        reg.record_call("skill-a")
        reg.record_call("skill-a")
        assert skill_a.call_count == 3
