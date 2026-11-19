"""Small command-line surface for artifact validation."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .provenance import validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="primekg-repurpose")
    subcommands = parser.add_subparsers(dest="command", required=True)
    reproduction = subcommands.add_parser("reproduce", help="CPU-only supported paper results with explicit evidence classes")
    reproduction.add_argument("--repository-root", type=Path, help="checkout containing artifacts/ and the claim manifest")
    reproduction.add_argument("--output", type=Path, default=Path("work/reproduction"), help="generated outputs, separate from reference inputs")
    command = subcommands.add_parser("validate", help="validate frozen artifacts and provenance")
    command.add_argument("--tier", choices=("smoke", "reference", "full-local"), default="reference")
    command.add_argument("--data-root", type=Path, help="artifact root; takes priority over PRIMEKG_DATA_ROOT")
    command.add_argument("--registry", type=Path, help="registry JSON (normally the repository registry)")
    command.add_argument("--benchmark-semantics", action="store_true", help="audit frozen CANONICAL_1HOP folds after artifact validation")
    command.add_argument("--json-report", type=Path, help="write a structured JSON report")
    rebuild = subcommands.add_parser("reconstruct-benchmark", help="rebuild P1-v0 from exact hash-verified PrimeKG")
    rebuild.add_argument("--data-root", type=Path, help="root containing registry logical raw/kg.csv")
    rebuild.add_argument("--raw-kg", type=Path, help="explicit location of registered raw/kg.csv, still hash-verified")
    rebuild.add_argument("--registry", type=Path, help="Gate-1 registry JSON")
    rebuild.add_argument("--frozen-root", type=Path, help="root of immutable frozen references")
    rebuild.add_argument("--output-dir", type=Path, help="separate generated-artifact directory")
    rebuild.add_argument("--json-report", type=Path, help="structured equivalence report")
    evaluator_command = subcommands.add_parser("reproduce-evaluator", help="recompute v1.1 tie-safe metrics from frozen score archives")
    evaluator_command.add_argument("--registry", type=Path, help="Gate-1 registry JSON")
    evaluator_command.add_argument("--frozen-root", type=Path, help="immutable frozen benchmark/reference root")
    evaluator_command.add_argument("--data-root", type=Path, help="root containing external score archives")
    evaluator_command.add_argument("--score-archive", action="append", default=[], metavar="ARTIFACT_ID=PATH", help="explicit local score archive path for a registered artifact")
    evaluator_command.add_argument("--json-report", type=Path, help="structured evaluator report")
    e1_command = subcommands.add_parser("reproduce-e1", help="run Gate-4 E1 and compare exact historical scores and frozen metrics")
    e1_command.add_argument("--registry", type=Path, help="Gate-1 registry JSON")
    e1_command.add_argument("--frozen-root", type=Path, help="immutable frozen benchmark/reference root")
    e1_command.add_argument("--raw-kg", type=Path, help="exact registered raw PrimeKG kg.csv")
    e1_command.add_argument("--historical-score", type=Path, help="recovered Cell-14 score archive")
    e1_command.add_argument("--historical-source", type=Path, help="hash-registered Cell-14 source")
    e1_command.add_argument("--generated-score", type=Path, help="separate clean generated score archive")
    e1_command.add_argument("--json-report", type=Path, help="structured Gate-4 equivalence report")
    e2_command = subcommands.add_parser("reproduce-e2", help="run Gate-5 E2 and compare exact historical scores and frozen metrics")
    e2_command.add_argument("--registry", type=Path, help="Gate-1 registry JSON")
    e2_command.add_argument("--frozen-root", type=Path, help="immutable frozen benchmark/reference root")
    e2_command.add_argument("--raw-kg", type=Path, help="exact registered raw PrimeKG kg.csv")
    e2_command.add_argument("--historical-score", type=Path, help="recovered Cell-17 score archive")
    e2_command.add_argument("--historical-source", type=Path, help="hash-registered Cell-17 source")
    e2_command.add_argument("--generated-score", type=Path, help="separate clean generated score archive")
    e2_command.add_argument("--json-report", type=Path, help="structured Gate-5 equivalence report")
    e3_command = subcommands.add_parser("prepare-e3", help="validate E3 Gate-6A inputs/checkpoints and freeze Gate-6B; never trains")
    e3_command.add_argument("--raw-kg", type=Path, help="optional exact PrimeKG kg.csv for streaming corpus reconstruction")
    e3_command.add_argument("--json-report", type=Path, help="Gate-6A report (default outputs/gate6a_e3_preparation.json)")
    e3_command.add_argument("--preregistration", type=Path, help="Gate-6B preregistration (default outputs/gate6b_preregistration.json)")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    if args.command == "reproduce":
        from .reproduction import reproduce
        repository = args.repository_root or (root if (root / "artifacts/registry.json").is_file() else Path.cwd())
        try:
            report = reproduce(repository, args.output)
        except (OSError, ValueError, KeyError, ImportError) as exc:
            print(f"Reproduction failed: {exc}")
            return 1
        print(f"Supported reproduction: {report['status']}")
        print(f"Outputs: {args.output.resolve()}")
        print("Classes 1/2 are computed; class 3 is historical replay; class 4 remains unsupported.")
        print("Complete independent paper/model reproduction: False; see equivalence_report.json and LIMITATIONS.md")
        return 0 if report["status"] == "PASS" else 1
    if args.command == "prepare-e3":
        from .gate6a import prepare_gate6a, write_json

        report_path = args.json_report or root / "outputs/gate6a_e3_preparation.json"
        prereg_path = args.preregistration or root / "outputs/gate6b_preregistration.json"
        report, prereg = prepare_gate6a(root, args.raw_kg)
        write_json(report, report_path)
        write_json(prereg, prereg_path)
        print(f"Gate: {report['gate']}")
        print(f"Corpus: {report['corpus']['status']}")
        print(f"Raw reconstruction: {report['raw_reconstruction']['status']}")
        for item in report["checkpoint_validation"]:
            print(f"Seed {item['seed']} checkpoint: strict={item['strict_load']} probe_max_abs_diff={item['probe_max_abs_difference']}")
        print(f"Score archives: {sum(x['status'] == 'PASS' for x in report['score_archives'])}/3 PASS")
        print(f"Applicable: {report['applicability']['applicable']} / {report['applicability']['total']}")
        print("Training launched: False")
        print(f"Overall: {report['overall_status']}")
        return 0 if report["overall_status"] == "PASS" else 1
    if args.command == "reproduce-e2":
        from .gate5 import reproduce_e2_gate5, write_report

        registry = args.registry or root / "artifacts/registry.json"
        frozen_root = args.frozen_root or root / "artifacts/frozen"
        raw_kg = args.raw_kg or (Path(os.environ["PRIMEKG_FULL_LOCAL_RAW"]) if os.environ.get("PRIMEKG_FULL_LOCAL_RAW") else None)
        historical_score = args.historical_score or root / "artifacts/recovered/external/p1_e2_disease_profile_label_transfer_scores.npz"
        historical_source = args.historical_source or root / "work/phase2_inputs/primekg_codex_ingest/source/authoritative/E2_authoritative.py"
        generated_score = args.generated_score or root / "artifacts/generated/e2/p1_e2_disease_profile_label_transfer_scores_clean.npz"
        report = reproduce_e2_gate5(
            root=root,
            registry_path=registry,
            frozen_root=frozen_root,
            raw_kg=raw_kg,
            historical_score=historical_score,
            historical_source=historical_source,
            generated_score=generated_score,
        )
        if args.json_report:
            write_report(report, args.json_report)
        score = report.get("score_equivalence", {})
        evaluation = report.get("evaluator_equivalence", {})
        print(f"Expert: {report['expert_id']} {report['expert_version']}")
        print(f"Protocol: {report['masking_protocol']}")
        print(f"Applicable: {report.get('applicable_count', 0)} / {report.get('disease_count', 0)}")
        if score:
            print(f"Scores unequal: {score.get('unequal_value_count')} max_abs_diff={score.get('max_absolute_difference')}")
        if evaluation:
            print(f"Macro Recall@50: {evaluation.get('macro_recall50_clean')}")
            print(f"Evaluator max_abs_diff: {evaluation.get('max_absolute_disease_level_difference')}")
        if report.get("error"):
            print(f"Error: {report['error']}")
        print(f"Overall: {report['overall_status']}")
        return 0 if report["overall_status"] == "PASS" else 1
    if args.command == "reproduce-e1":
        from .gate4 import reproduce_e1_gate4, write_report

        registry = args.registry or root / "artifacts/registry.json"
        frozen_root = args.frozen_root or root / "artifacts/frozen"
        raw_kg = args.raw_kg or (Path(os.environ["PRIMEKG_FULL_LOCAL_RAW"]) if os.environ.get("PRIMEKG_FULL_LOCAL_RAW") else None)
        historical_score = args.historical_score or root / "artifacts/recovered/external/p1_e1_weighted_gene_cosine_scores.npz"
        historical_source = args.historical_source or root / "work/phase2_inputs/primekg_codex_ingest/source/authoritative/E1_authoritative.py"
        generated_score = args.generated_score or root / "artifacts/generated/e1/p1_e1_weighted_gene_cosine_scores_clean.npz"
        report = reproduce_e1_gate4(
            root=root,
            registry_path=registry,
            frozen_root=frozen_root,
            raw_kg=raw_kg,
            historical_score=historical_score,
            historical_source=historical_source,
            generated_score=generated_score,
        )
        if args.json_report:
            write_report(report, args.json_report)
        score = report.get("score_equivalence", {})
        evaluation = report.get("evaluator_equivalence", {})
        print(f"Expert: {report['expert_id']} {report['expert_version']}")
        print(f"Applicable: {report.get('applicable_count', 0)} / {report.get('disease_count', 0)}")
        if score:
            print(f"Scores unequal: {score.get('unequal_value_count')} max_abs_diff={score.get('max_absolute_difference')}")
        if evaluation:
            print(f"Macro Recall@50: {evaluation.get('macro_recall50_clean')}")
            print(f"Evaluator max_abs_diff: {evaluation.get('max_absolute_disease_level_difference')}")
        if report.get("error"):
            print(f"Error: {report['error']}")
        print(f"Overall: {report['overall_status']}")
        return 0 if report["overall_status"] == "PASS" else 1
    if args.command == "reproduce-evaluator":
        from .evaluation import SCORE_TO_MATRIX, evaluator_formula_self_checks, load_frozen_evaluator, reproduce_archive

        registry = args.registry or root / "artifacts/registry.json"
        frozen_root = args.frozen_root or root / "artifacts/frozen"
        data_root = args.data_root or Path(os.environ.get("PRIMEKG_DATA_ROOT", frozen_root))
        report = {"benchmark_id": "P1_TRACK_A_PRIMEKG_V0", "evaluator_version": "1.1_tiesafe", "status": "NOT_RUN", "candidate_axis_verified": False, "metric_policy": None, "fixture_checks": evaluator_formula_self_checks(), "archives_tested": [], "unavailable_score_archives": []}
        try:
            overrides = {}
            for entry in args.score_archive:
                if "=" not in entry:
                    raise ValueError("--score-archive requires ARTIFACT_ID=PATH")
                artifact_id, path_text = entry.split("=", 1)
                if artifact_id not in SCORE_TO_MATRIX or artifact_id in overrides:
                    raise ValueError("unknown or duplicate score artifact ID")
                overrides[artifact_id] = Path(path_text)
            evaluator, contract = load_frozen_evaluator(registry, frozen_root)
            report["candidate_axis_verified"] = True
            report["disease_axis_verified"] = True
            report["metric_policy"] = contract["metric_policy"]
            report["k_values"] = list(evaluator.k_values)
            report["gate1_reference_overall"] = contract["gate1_overall"]
            for artifact_id in SCORE_TO_MATRIX:
                path = overrides.get(artifact_id, data_root / artifact_id)
                if path.is_file():
                    report["archives_tested"].append(reproduce_archive(artifact_id, path, frozen_root, registry, evaluator))
                else:
                    report["unavailable_score_archives"].append({"artifact_id": artifact_id, "state": "REGISTERED_EXTERNAL_NOT_LOCAL"})
            if report["fixture_checks"]["status"] != "PASS" or any(row["status"] != "PASS" for row in report["archives_tested"]):
                report["status"] = "FAIL"
            elif report["archives_tested"]:
                report["status"] = "PASS"
            else:
                report["status"] = "REGISTERED_EXTERNAL_NOT_LOCAL"
        except (OSError, ValueError, ArithmeticError, KeyError) as exc:
            report["status"] = "FAIL"
            report["error"] = str(exc)
        if args.json_report:
            args.json_report.parent.mkdir(parents=True, exist_ok=True)
            args.json_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Benchmark: {report['benchmark_id']}")
        print(f"Evaluator: {report['evaluator_version']}")
        print(f"Candidate axis verified: {report['candidate_axis_verified']}")
        print(f"Fixture checks: {report['fixture_checks']['status']}")
        for archive in report["archives_tested"]:
            print(f"{archive['score_artifact_id']}: {archive['status']} max_abs_diff={archive['max_absolute_difference']:.3g} macro_Recall@50={archive['macro_recall50_computed']:.16g}")
        print(f"Unavailable score archives: {len(report['unavailable_score_archives'])}")
        if report.get("error"):
            print(f"Error: {report['error']}")
        print(f"Overall: {report['status']}")
        return 0 if report["status"] == "PASS" else 1
    if args.command == "reconstruct-benchmark":
        from .reconstruction import compare_artifacts, reconstruct, validate_reconstruction_counts, verified_raw_path

        registry = args.registry or root / "artifacts/registry.json"
        data_root = args.data_root or Path(os.environ.get("PRIMEKG_DATA_ROOT", root / "artifacts/frozen"))
        frozen_root = args.frozen_root or root / "artifacts/frozen"
        output_dir = args.output_dir or root / "artifacts/generated/benchmark_reconstruction"
        report = {"benchmark_id": "P1_TRACK_A_PRIMEKG_V0", "status": "NOT_RUN", "raw_input": None, "reconstruction": None, "count_checks": [], "artifacts": []}
        try:
            generated_resolved = output_dir.resolve()
            frozen_resolved = frozen_root.resolve()
            if generated_resolved.is_relative_to(frozen_resolved) or frozen_resolved.is_relative_to(generated_resolved):
                raise ValueError("generated output directory must be separate from frozen references")
            raw, raw_report = verified_raw_path(registry, data_root, args.raw_kg)
            report["raw_input"] = raw_report
            if raw is None:
                report["status"] = raw_report["status"]
            else:
                report["reconstruction"] = reconstruct(raw, output_dir)
                report["count_checks"] = validate_reconstruction_counts(report["reconstruction"], registry, frozen_root)
                report["artifacts"] = compare_artifacts(output_dir, frozen_root, registry)
                science_ok = all(item["semantic_equivalence"] for item in report["artifacts"]) and all(check["pass"] for check in report["count_checks"])
                report["status"] = "PASS" if science_ok else "SCIENTIFIC_DIVERGENCE"
                report["generated_output_dir"] = str(output_dir)
        except (OSError, ValueError, KeyError) as exc:
            report["status"] = "FAIL"
            report["error"] = str(exc)
        if args.json_report:
            args.json_report.parent.mkdir(parents=True, exist_ok=True)
            args.json_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Benchmark: {report['benchmark_id']}")
        print(f"Raw: {report['raw_input']['status'] if report['raw_input'] else 'unavailable'}")
        if report["reconstruction"]:
            print(f"Directed rows: {report['reconstruction']['census']['directed_rows']}")
            print(f"Primary diseases: {report['reconstruction']['primary_diseases']}")
            print(f"Primary truth: {report['reconstruction']['primary_truth']}")
            for item in report["artifacts"]:
                print(f"{item['artifact']}: {item['classification']}")
        if report.get("error"):
            print(f"Error: {report['error']}")
        print(f"Overall: {report['status']}")
        return 0 if report["status"] == "PASS" else 1
    if args.tier == "smoke" and args.registry is None:
        registry = root / "tests/fixtures/registry.json"
        data_root = args.data_root or root / "tests/fixtures/data"
    else:
        registry = args.registry or root / "artifacts/registry.json"
        # Explicit CLI path overrides environment, then the documented default.
        data_root = args.data_root or Path(os.environ.get("PRIMEKG_DATA_ROOT", root / "artifacts/frozen"))
    report = validate(registry, data_root, args.tier.upper().replace("-", "_"))
    if args.benchmark_semantics:
        if args.tier == "smoke":
            parser.error("--benchmark-semantics requires reference or full-local tier")
        from .benchmark import load_frozen_benchmark, validate_frozen_semantics

        try:
            frozen = load_frozen_benchmark(registry, data_root, report)
            semantics = validate_frozen_semantics(frozen)
        except (OSError, ValueError) as exc:
            semantics = {"status": "FAIL", "failures": [{"field": "integrity_boundary", "expected": "verified frozen inputs", "observed": str(exc), "severity": "ERROR"}], "folds": []}
        report["benchmark_semantics"] = semantics
        if semantics["status"] == "FAIL":
            report["failures"].extend({"artifact_id": "benchmark_semantics", **failure} for failure in semantics["failures"])
            report["required_failure"] = True
            report["overall"] = "FAIL"
    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Benchmark: {report['benchmark_id']}")
    print(f"Tier: {report['tier']}")
    for state, count in sorted(report["summary"].items()):
        print(f"{state}: {count}")
    print(f"Failures: {len(report['failures'])}")
    if args.benchmark_semantics:
        semantics = report["benchmark_semantics"]
        print(f"Protocol: {semantics.get('protocol_id', 'unavailable')}")
        for fold in semantics.get("folds", []):
            print(f"Fold {fold['fold']}: target={fold.get('target_count')} buffer={fold.get('buffer_count')} legal_CLEAN={fold.get('legal_clean_training_count')} direct_leaks={fold.get('surviving_direct_ontology_leakage_paths')} {fold['status']}")
        print(f"Benchmark semantics: {semantics['status']}")
    if report["failures"]:
        for failure in report["failures"][:10]:
            print(f"  {failure['artifact_id']} {failure['field']}: expected {failure['expected']!r}; observed {failure['observed']!r}")
        if len(report["failures"]) > 10:
            print(f"  ... {len(report['failures']) - 10} more in JSON report")
    print(f"Overall: {report['overall']}")
    return 1 if report["required_failure"] else 0
