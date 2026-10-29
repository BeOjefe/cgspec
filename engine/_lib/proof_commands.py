"""Create signed proof seals and integration mappings from trusted CI inputs."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from .common import CgspecError, PROJECT_FILE, utc_now, write_json
from .gitview import git
from .proof_seals import NAMESPACE, canonical, digest, mapping_errors, pair_binding_errors, seal_errors

ARGUMENTS = ("--pair", "--pair-path", "--red", "--green", "--review", "--seal-id", "--identity",
             "--provider", "--workflow", "--signing-key", "--output", "--seal", "--seal-path",
             "--map-id", "--strategy", "--integrated-revision", "--pull-request", "--revalidation-json")


def add_arguments(parser) -> None:
    for name in ARGUMENTS:
        parser.add_argument(name)


def _json(path: Path) -> tuple[dict, bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise CgspecError(f"cannot read trusted proof input {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CgspecError(f"trusted proof input {path} must be an object")
    return value, raw


def _at(root: Path, revision: str, rel: str) -> bytes:
    shown = git(root, "show", f"{revision}:{rel}", binary=True)
    if shown.returncode:
        raise CgspecError(f"cannot bind missing content {rel} at {revision[:12]}")
    return shown.stdout


def _sign(record: dict, key: Path) -> dict:
    record["attestation"]["signature"] = ""
    try:
        with tempfile.TemporaryDirectory(prefix="cgspec-sign-") as directory:
            payload = Path(directory) / "payload"
            payload.write_bytes(canonical(record))
            result = subprocess.run(["ssh-keygen", "-Y", "sign", "-q", "-f", str(key),
                                     "-n", NAMESPACE, str(payload)], capture_output=True, text=True)
            if result.returncode:
                raise CgspecError(f"cannot sign proof record: {result.stderr.strip()}")
            record["attestation"]["signature"] = payload.with_suffix(".sig").read_text()
    except OSError as exc:
        raise CgspecError(f"cannot sign proof record: {exc}") from exc
    return record


def _attestation(args) -> dict:
    required = ("identity", "provider", "workflow", "run_id", "signing_key")
    missing = [name.replace("_", "-") for name in required if not getattr(args, name, None)]
    if missing:
        raise CgspecError("proof signing needs --" + ", --".join(missing))
    return {"identity": args.identity, "provider": args.provider, "workflow": args.workflow,
            "run_id": args.run_id, "signed_at": utc_now(), "signature": ""}


def _phase(detail: dict, raw: bytes, expected: str) -> dict:
    fingerprints = detail.get("fingerprints", {})
    if detail.get("result") != expected or not isinstance(fingerprints, dict):
        raise CgspecError(f"proof detail must report {expected}")
    return {"revision": detail.get("revision", ""), "result": expected,
            "detail_sha256": digest(raw), "runner_id": detail.get("runner_id", ""),
            "runner_hash": fingerprints.get("runner", ""),
            "environment_hash": fingerprints.get("environment", ""),
            "test_sha256": detail.get("test_sha256", "")}


def create_seal(root: Path, args) -> Path:
    pair, pair_raw = _json(Path(args.pair))
    red, red_raw = _json(Path(args.red))
    green, green_raw = _json(Path(args.green))
    review, review_raw = _json(Path(args.review))
    head = green.get("revision", "")
    if git(root, "merge-base", "--is-ancestor", args.base or "", head).returncode:
        raise CgspecError("reviewed head must descend from the protected base")
    if review.get("verdict") != "PASS" or review.get("revision") != head or not review.get("ran_by"):
        raise CgspecError("independent review must be PASS and bind the green revision")
    for label, detail in (("red", red), ("green", green)):
        if (detail.get("proof_file") != args.pair_path or detail.get("test_id") != pair.get("test_id")
                or detail.get("candidate_revision") != head):
            raise CgspecError(f"{label} detail does not identify this test-pair and reviewed candidate")
    paths = [pair.get("test_file"), PROJECT_FILE.as_posix(), *pair.get("covers", [])]
    semantics = pair.get("test_semantics", {})
    paths += [item.get("path") for item in semantics.get("dependencies", []) if isinstance(item, dict)]
    fingerprints = green.get("fingerprints", {})
    paths += list(fingerprints.get("inputs", {})) if isinstance(fingerprints, dict) else []
    content = {rel: digest(_at(root, head, rel)) for rel in dict.fromkeys(paths) if isinstance(rel, str)}
    outcomes = [item for item in (args.outcomes or "").split(",") if item]
    if _at(root, head, args.pair_path) != pair_raw:
        raise CgspecError("test-pair input differs from the reviewed revision")
    seal = {"schema": 1, "seal_id": args.seal_id, "test_pair": args.pair_path,
            "test_pair_sha256": digest(pair_raw), "test_id": pair.get("test_id"), "outcomes": outcomes,
            "reviewed_base": args.base, "reviewed_head": head,
            "red": _phase(red, red_raw, "ASSERTION_FAILED"),
            "green": _phase(green, green_raw, "PASS"), "content": content,
            "review": {"reviewer": review["ran_by"], "revision": head,
                       "record_sha256": digest(review_raw)}, "attestation": _attestation(args)}
    project = json.loads(_at(root, args.base, PROJECT_FILE.as_posix()))
    _sign(seal, Path(args.signing_key))
    problems = seal_errors(seal, project) + pair_binding_errors(seal, pair_raw)
    if problems:
        raise CgspecError("invalid generated proof seal: " + "; ".join(problems))
    output = Path(args.output)
    write_json(output, seal)
    return output


def create_mapping(root: Path, args) -> Path:
    seal, seal_raw = _json(Path(args.seal))
    differences = []
    for path, sealed_hash in seal.get("content", {}).items():
        try:
            integrated_hash = digest(_at(root, args.integrated_revision, path))
        except CgspecError:
            integrated_hash = "0" * 64
        if integrated_hash != sealed_hash:
            revalidation = (args.revalidation or {}).get(path)
            if not revalidation:
                raise CgspecError(f"{path}: material difference needs a signed revalidation seal")
            differences.append({"path": path, "sealed_sha256": sealed_hash,
                                "integrated_sha256": integrated_hash, "revalidation": revalidation})
    mapping = {"schema": 1, "map_id": args.map_id, "seal": args.seal_path,
               "seal_sha256": digest(seal_raw), "strategy": args.strategy,
               "integrated_revision": args.integrated_revision, "pull_request": args.pull_request,
               "differences": differences, "mapped_at": utc_now(), "attestation": _attestation(args)}
    project = json.loads(_at(root, seal["reviewed_base"], PROJECT_FILE.as_posix()))
    _sign(mapping, Path(args.signing_key))
    problems = mapping_errors(root, mapping, seal_raw, project)
    if problems:
        raise CgspecError("invalid generated proof mapping: " + "; ".join(problems))
    output = Path(args.output)
    write_json(output, mapping)
    return output


def cli(root: Path, args) -> int:
    action = args.rest[0] if args.rest else ""
    if action == "seal":
        output = create_seal(root, args)
    elif action == "map":
        if args.revalidation_json:
            value, _ = _json(Path(args.revalidation_json))
            args.revalidation = value
        else:
            args.revalidation = {}
        output = create_mapping(root, args)
    else:
        raise CgspecError("usage: cgspec_hook.py proof seal|map [options]")
    print(output)
    return 0
