#Check  ReadME for instructions to run.

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

EXAMPLES = {
    "1": {
        "input_dir": ROOT / "input_eg1",
        "output_dir": ROOT / "intermediate_outputs" / "eg1",
        "input_names": {
            "fsm1": "fsm_alpha10.json",
            "fsm2": "fsm_beta10.json",
            "interaction": "interaction_mapping.json",
            "variables": "variable_mapping.json",
        },
    },
    "2": {
        "input_dir": ROOT / "input_eg2",
        "output_dir": ROOT / "intermediate_outputs" / "eg2",
        "input_names": {
            "fsm1": "fsm_alpha2.json",
            "fsm2": "fsm_beta2.json",
            "interaction": "interaction_mapping2.json",
            "variables": "variable_mapping2.json",
        },
    },
}
OUTPUT_NAMES = {
    "composed": "composed_fsm.json",
    "knowledge": "compatibility_knowledge.json",
    "rules": "verification_rules.json",
    "smv": "verification_model.smv",
    "nusmv": "nusmv_output.txt",
    "parsed": "parsed_counterexamples.json",
    "conflicts": "compatibility_conflicts.json",
    "report": "compatibility_report.json",
}


def load_module(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(module_name, SRC / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def ensure_inputs(input_dir: Path, input_names: dict[str, str]) -> dict[str, Path]:
    paths = {key: input_dir / name for key, name in input_names.items()}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing required input file(s):\n  " + "\n  ".join(missing)
            + "\nExpected the four input files in the selected input folder."
        )
    return paths


def prepare(example: str, config: dict) -> None:
    inputs = ensure_inputs(config["input_dir"], config["input_names"])
    out = config["output_dir"]
    out.mkdir(parents=True, exist_ok=True)

    composer = load_module("fsm_composer", "fsm_composerv3.py")
    fsm1 = composer.load_fsm(inputs["fsm1"])
    fsm2 = composer.load_fsm(inputs["fsm2"])
    interaction = composer.load_interaction_mapping(inputs["interaction"])
    variable_map = composer.load_variable_mapping(inputs["variables"])
    composed = composer.compose_fsms(fsm1, fsm2, interaction, variable_map)
    composer.save_model(composed, out / OUTPUT_NAMES["composed"])


    with (out / OUTPUT_NAMES["composed"]).open("r", encoding="utf-8") as f:
        composed = json.load(f)
    print(f"[1/5] FSM composition complete: {len(composed['states'])} states, {len(composed['transitions'])} transitions")

    analyzer = load_module("compatibility_analyzer", "compatiblity_analyzerv3.py")
    workflow = analyzer.workflow_analysis(composed)
    transitions = analyzer.transition_analysis(composed)
    synchronization = analyzer.synchronization_analysis(transitions)
    knowledge = {
        "workflow_analysis": workflow,
        "transition_analysis": transitions,
        "milestone_observations": analyzer.milestone_observations(composed),
        "synchronization_analysis": synchronization,
        "compatibility_assessment": analyzer.compatibility_assessment(synchronization),
    }
    with (out / OUTPUT_NAMES["knowledge"]).open("w", encoding="utf-8") as f:
        json.dump(knowledge, f, indent=4)
    print("[2/5] Compatibility analysis complete")

    rule_gen = load_module("rule_generator", "rule_generator_v3.2.py")
    rules = rule_gen.build_rule_set(knowledge)
    rule_gen.write_rules(rules, out / OUTPUT_NAMES["rules"])
    print("[3/5] Verification rules generated")

    smv_gen = load_module("verification_model_generator", "verification_model_generator_test.py")
    state_dictionary = smv_gen.build_state_dictionary(composed)
    guard_lookup = smv_gen.build_guard_lookup(rules)
    smv_lines = smv_gen.generate_module()
    smv_lines.extend(smv_gen.generate_var_section(composed))
    smv_lines.extend(smv_gen.generate_define_section(state_dictionary))
    smv_lines.extend(smv_gen.generate_assign_header(composed))
    smv_lines.extend(smv_gen.generate_variable_initialization(composed))
    smv_lines.extend(smv_gen.generate_transition_section(composed, guard_lookup))
    smv_gen.append_specifications(smv_lines, rules)
    smv_gen.save_model(smv_lines, out / OUTPUT_NAMES["smv"])
    print("[4/5] NuSMV model generated")

    print("\n[5/5] MANUAL NuSMV step required")
    print(f"Open this file in NuSMV: {out / OUTPUT_NAMES['smv']}")
    print("Run NuSMV in Ubuntu and save/copy its complete output to:")
    print(f"{out / OUTPUT_NAMES['nusmv']}")
    print(f"Then resume with: python main.py --example {example} --stage postprocess")


def postprocess(example: str, config: dict) -> None:
    out = config["output_dir"]
    required = [OUTPUT_NAMES[k] for k in ("nusmv", "rules", "knowledge")]
    missing = [name for name in required if not (out / name).is_file()]
    if missing:
        raise FileNotFoundError("Cannot resume; missing file(s) in " + str(out) + ": " + ", ".join(missing))

    parser_mod = load_module("counterexample_parser", "parser.py")
    parser = parser_mod.CounterexampleParser(
        nusmv_output_file=out / OUTPUT_NAMES["nusmv"],
        rules_file=out / OUTPUT_NAMES["rules"],
        output_file=out / OUTPUT_NAMES["parsed"],
    )
    parser.run()
    print("[1/3] Counterexample parsing complete")

    classifier_mod = load_module("conflict_classifier", "conflict_classification.py")
    classifier = classifier_mod.CompatibilityClassifier(
        input_file=out / OUTPUT_NAMES["parsed"],
        output_file=out / OUTPUT_NAMES["conflicts"],
    )
    classifier.run()
    print("[2/3] Conflict classification complete")

    report_mod = load_module("compatibility_report", "compatiblity_report_generator.py")
    report = report_mod.CompatibilityReportGenerator(
        input_file=out / OUTPUT_NAMES["conflicts"],
        output_file=out / OUTPUT_NAMES["report"],
        analysis_file=out / OUTPUT_NAMES["knowledge"],
    )
    report.run()
    print("[3/3] Final compatibility report generated")
    print(f"Report: {out / OUTPUT_NAMES['report']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one Project Recon experiment pipeline.")
    parser.add_argument("--example", choices=EXAMPLES, required=True, help="Experiment to run: 1 or 2")
    parser.add_argument("--stage", choices=("prepare", "postprocess"), default="prepare",
                        help="prepare creates the SMV model; postprocess consumes manual NuSMV output")
    args = parser.parse_args()
    config = EXAMPLES[args.example]
    print(f"Project Recon | Example {args.example}")
    print(f"Inputs:  {config['input_dir']}")
    print(f"Outputs: {config['output_dir']}\n")
    if args.stage == "prepare":
        prepare(args.example, config)
    else:
        postprocess(args.example, config)


if __name__ == "__main__":
    main()
