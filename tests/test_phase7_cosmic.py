"""Phase 7 Cosmic tests — Nature/ICLR/5D-World-Model grade."""
import pytest

class TestAutoScientist:
    def test_hypothesize(self):
        from kernel.cosmic.auto_scientist import AutoScientist
        s = AutoScientist(); s.ground_literature("biomedical","cancer drug")
        hyps = s.generate_hypotheses("biomedical","kinase inhibitor",3)
        assert len(hyps) == 3
    def test_experiment_design(self):
        from kernel.cosmic.auto_scientist import AutoScientist
        s = AutoScientist(); s.generate_hypotheses("test","ctx",1)
        exp = s.design_experiment(s._hypotheses[0].id)
        assert exp is not None
        assert exp.status == "designed"
    def test_validate_and_report(self):
        from kernel.cosmic.auto_scientist import AutoScientist
        s = AutoScientist(); s.generate_hypotheses("test","ctx",2)
        exp = s.design_experiment(s._hypotheses[0].id)
        s.validate(exp.id,{"p_value":0.01})
        r = s.generate_report()
        assert r["experiments_completed"] == 1

class TestCodeBootstrap:
    def test_bootstrap(self):
        from kernel.cosmic.code_bootstrap import CodeBootstrap
        r = CodeBootstrap().bootstrap("A self-reproducing coding agent")
        assert r.success is True
        assert r.self_reproduced is True
    def test_meta_circular(self):
        from kernel.cosmic.code_bootstrap import CodeBootstrap
        cb = CodeBootstrap()
        spec = cb.generate_spec("test agent")
        code = cb.generate_agent_code(spec)
        assert cb.verify_meta_circular(code, spec)

class TestWorldModel:
    def test_observe_and_predict(self):
        from kernel.cosmic.world_model import WorldModel
        wm = WorldModel()
        sid = wm.observe([{"type":"agent"},{"type":"tool"}])
        p = wm.predict_next(sid,"analyze")
        assert p["level"] == "L1_Predictor"
    def test_simulate(self):
        from kernel.cosmic.world_model import WorldModel
        wm = WorldModel()
        sid = wm.observe([{"type":"node"}])
        rollout = wm.simulate(sid,["plan","exec","verify"],5)
        assert len(rollout) == 5
    def test_5d_futures(self):
        from kernel.cosmic.world_model import WorldModel
        wm = WorldModel()
        sid = wm.observe([{"type":"agent"}])
        futures = wm.explore_futures(sid,[["a","b"],["c","d"],["e","f"]])
        assert len(futures) == 3
        best = wm.best_action(sid,[["a","b"],["c","d"]])
        assert isinstance(best,list)
    def test_revise(self):
        from kernel.cosmic.world_model import WorldModel
        wm = WorldModel()
        r = wm.revise({"entity_count":3},{"entity_count":5})
        assert r["revised"] is True

class TestRecursiveSelf:
    def test_improve_micro(self):
        from kernel.cosmic.recursive_self import RecursiveSelfImprover
        ri = RecursiveSelfImprover()
        ri.register_module("test","def f(): return sum(range(10))\nprint(f())")
        r = ri.improve_cycle(level="micro")
        assert r["level"] == "micro"
    def test_improve_macro(self):
        from kernel.cosmic.recursive_self import RecursiveSelfImprover
        ri = RecursiveSelfImprover()
        ri.register_module("test","def f(): return 42")
        r = ri.improve_cycle(level="macro")
        assert r["total_modules"] == 1
    def test_status(self):
        from kernel.cosmic.recursive_self import RecursiveSelfImprover
        ri = RecursiveSelfImprover()
        ri.register_module("a","def f(): return 1")
        ri.improve_cycle(level="meta")
        s = ri.get_status()
        assert s["modules"] >= 1

class TestDigitalTwin:
    def test_sync(self):
        from kernel.cosmic.digital_twin import CognitiveDigitalTwin
        twin = CognitiveDigitalTwin("test")
        s = twin.sync({"cpu":50,"memory":4096})
        assert "cpu" in s.metrics
    def test_intervene(self):
        from kernel.cosmic.digital_twin import CognitiveDigitalTwin
        twin = CognitiveDigitalTwin("test")
        s = twin.sync({"cpu":100,"memory":100})  # big jump
        invs = twin.analyze_and_intervene(s)
        assert isinstance(invs,list)
    def test_decide(self):
        from kernel.cosmic.digital_twin import CognitiveDigitalTwin
        twin = CognitiveDigitalTwin("test")
        decisions = twin.autonomous_decide([])
        assert isinstance(decisions,list)

class TestCosmicMCPTools:
    def test_all_registered(self):
        from mcp.server import SclerotiumMCPServer
        s = SclerotiumMCPServer(); s.register_all_tools()
        for n in ["scientist_hypothesize","bootstrap_cycle","world_simulate",
                   "world_futures","recursive_improve","digital_twin_sync"]:
            assert s.tools.get_handler(n) is not None, f"Missing: {n}"
