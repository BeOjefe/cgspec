"""Trusted proof seals and post-integration mappings for rewritten Git history."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from .common import PROJECT_FILE
from .gitview import View, git
from .schema import validate_named

SEALS = "docs/_cgspec/06-evidence/seals"
MAPS = "docs/_cgspec/06-evidence/integrations"
NAMESPACE = "cgspec-proof"


def _load(raw: bytes | None) -> dict:
    try:
        value = json.loads(raw.decode("utf-8")) if raw else {}
        return value if isinstance(value, dict) else {}
    except (UnicodeDecodeError, ValueError):
        return {}


def canonical(record: dict) -> bytes:
    value = json.loads(json.dumps(record))
    if isinstance(value.get("attestation"), dict):
        value["attestation"]["signature"] = ""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _signer(record: dict, project: dict) -> tuple[dict | None, str | None]:
    attestation = record.get("attestation", {})
    identity = attestation.get("identity")
    matches = [item for item in project.get("proof_signers", [])
               if isinstance(item, dict) and item.get("identity") == identity]
    if len(matches) != 1:
        return None, f"attestation identity {identity!r} is not uniquely trusted"
    signer = matches[0]
    if signer.get("provider") != attestation.get("provider") or signer.get("workflow") != attestation.get("workflow"):
        return None, "attestation provider/workflow differs from the protected signer policy"
    if any("\n" in str(signer.get(key, "")) for key in ("identity", "public_key")):
        return None, "trusted proof signer contains an unsafe newline"
    return signer, None


def verify_attestation(record: dict, project: dict) -> str | None:
    signer, problem = _signer(record, project)
    if problem:
        return problem
    signature = str(record.get("attestation", {}).get("signature", ""))
    if not signature:
        return "attestation has no detached signature"
    try:
        with tempfile.TemporaryDirectory(prefix="cgspec-seal-") as directory:
            allowed = Path(directory) / "allowed_signers"
            signed = Path(directory) / "signature"
            allowed.write_text(f"{signer['identity']} {signer['public_key']}\n")
            signed.write_text(signature)
            result = subprocess.run(["ssh-keygen", "-Y", "verify", "-f", str(allowed), "-I",
                                     signer["identity"], "-n", NAMESPACE, "-s", str(signed)],
                                    input=canonical(record), capture_output=True)
    except OSError as exc:
        return f"cannot verify proof attestation: {exc}"
    return None if result.returncode == 0 else "proof attestation signature is not trusted"


def _project_at(root: Path, revision: str) -> dict:
    return _load(_blob(root, revision, PROJECT_FILE.as_posix()))


def _blob(root: Path, revision: str, path: str) -> bytes | None:
    result = git(root, "show", f"{revision}:{path}", binary=True)
    return result.stdout if result.returncode == 0 else None


def seal_errors(seal: dict, project: dict) -> list[str]:
    errors = validate_named(seal, "proof-seal")
    if errors:
        return errors
    if seal["red"]["result"] != "ASSERTION_FAILED" or seal["green"]["result"] != "PASS":
        errors.append("seal phases must bind ASSERTION_FAILED red and PASS green results")
    if seal["review"]["revision"] != seal["reviewed_head"]:
        errors.append("independent review must bind the sealed reviewed_head")
    if seal["green"]["revision"] != seal["reviewed_head"]:
        errors.append("green proof must bind the sealed reviewed_head")
    if seal["red"]["test_sha256"] != seal["green"]["test_sha256"]:
        errors.append("red and green proof must bind the same test content")
    problem = verify_attestation(seal, project)
    return errors + ([problem] if problem else [])


def pair_binding_errors(seal: dict, pair_raw: bytes | None) -> list[str]:
    pair = _load(pair_raw)
    if not pair_raw or digest(pair_raw) != seal.get("test_pair_sha256"):
        return ["seal test-pair digest does not match its canonical record"]
    errors = []
    if seal.get("test_id") != pair.get("test_id"):
        errors.append("seal test_id differs from its test-pair")
    if seal.get("red", {}).get("revision") != pair.get("failed_at"):
        errors.append("seal red revision differs from test-pair failed_at")
    return errors


def _revalidation(root: Path, revision: str, path: str, expected: str, project: dict,
                  source_revision: str) -> str | None:
    raw = _blob(root, source_revision, path)
    record = _load(raw)
    if not raw or record.get("reviewed_head") != revision:
        return f"revalidation seal {path} is not bound to integrated revision {revision[:12]}"
    if problem := next(iter(seal_errors(record, project)), None):
        return f"revalidation seal {path}: {problem}"
    pair_raw = _blob(root, source_revision, record.get("test_pair", ""))
    if problem := next(iter(pair_binding_errors(record, pair_raw)), None):
        return f"revalidation seal {path}: {problem}"
    integrated = _blob(root, revision, expected)
    if record.get("content", {}).get(expected) != (digest(integrated) if integrated is not None else "0" * 64):
        return f"revalidation seal {path} does not bind changed path {expected}"
    return None


def mapping_errors(root: Path, mapping: dict, seal_raw: bytes | None, project: dict,
                   source_revision: str = "HEAD") -> list[str]:
    errors = validate_named(mapping, "proof-map")
    seal = _load(seal_raw)
    if errors:
        return errors
    if not seal_raw or digest(seal_raw) != mapping["seal_sha256"]:
        errors.append("integration mapping seal digest does not match the canonical seal record")
        return errors
    seal_project = _project_at(root, seal.get("reviewed_base", ""))
    errors += [f"seal: {error}" for error in seal_errors(seal, seal_project)]
    pair_raw = _blob(root, mapping["integrated_revision"], seal.get("test_pair", ""))
    errors += [f"seal: {error}" for error in pair_binding_errors(seal, pair_raw)]
    problem = verify_attestation(mapping, project)
    if problem:
        errors.append(problem)
    revision = mapping["integrated_revision"]
    differences = {item["path"]: item for item in mapping["differences"]}
    for path, sealed_hash in seal["content"].items():
        raw = _blob(root, revision, path)
        integrated_hash = digest(raw) if raw is not None else "0" * 64
        difference = differences.get(path)
        if integrated_hash == sealed_hash:
            if difference:
                errors.append(f"{path}: mapping declares a difference where content is unchanged")
            continue
        if not difference or difference["sealed_sha256"] != sealed_hash or difference["integrated_sha256"] != integrated_hash:
            errors.append(f"{path}: integrated content differs from the seal without an exact mapping")
            continue
        if problem := _revalidation(root, revision, difference["revalidation"], path, project, source_revision):
            errors.append(problem)
    unknown = set(differences) - set(seal["content"])
    errors += [f"{path}: difference is not part of the sealed relevant content" for path in sorted(unknown)]
    return errors


def record_errors(view: View, changes) -> list[str]:
    reasons = []
    for change in changes:
        if not change.path.startswith((SEALS + "/", MAPS + "/")) or not change.path.endswith(".json"):
            continue
        if change.status != "A":
            reasons.append(f"{change.path}: proof seals and integration mappings are immutable")
            continue
        record = _load(view.read_new(change.path))
        if change.path.startswith(SEALS + "/"):
            errors = seal_errors(record, _project_at(view.root, record.get("reviewed_base", "")))
            errors += pair_binding_errors(record, view.read_new(record.get("test_pair", "")))
        else:
            seal_raw = view.read_new(record.get("seal", ""))
            seal = _load(seal_raw)
            source_revision = view.new if view.new != ":" else "HEAD"
            project = _project_at(view.root, seal.get("reviewed_base", ""))
            errors = mapping_errors(view.root, record, seal_raw, project, source_revision)
            target = view.old if view.new != ":" else git(view.root, "rev-parse", "HEAD").stdout.strip()
            if record.get("integrated_revision") != target:
                errors.append("integration mapping must be an envelope around its integrated parent revision")
        reasons += [f"{change.path}: {error}" for error in errors]
    return reasons


def signer_policy_errors(view: View) -> list[str]:
    """Proof signer policy rotates only under pre-existing owner signing authority."""
    old = _load(view.read_old(PROJECT_FILE.as_posix())).get("proof_signers", [])
    new = _load(view.read_new(PROJECT_FILE.as_posix())).get("proof_signers", [])
    if old == new or view.new == ":":
        return []
    from .commit_trust import trusted_signature
    if trusted_signature(view):
        return []
    return ["project.json proof_signers changed without a commit signature from a previously trusted "
            "approver key; bootstrap requires a protected baseline or separately verified owner review"]


def historical_pair_error(view: View, pair_path: str, pair: dict) -> str | None:
    pair_raw = view.read_new(pair_path)
    candidate = view.new if view.new != ":" else git(view.root, "rev-parse", "HEAD").stdout.strip()
    found = False
    for map_path in view.files_new(MAPS):
        mapping = _load(view.read_new(map_path))
        seal_raw = view.read_new(mapping.get("seal", ""))
        seal = _load(seal_raw)
        if seal.get("test_pair") != pair_path or seal.get("test_pair_sha256") != digest(pair_raw or b""):
            continue
        found = True
        if git(view.root, "merge-base", "--is-ancestor", mapping.get("integrated_revision", ""), candidate).returncode:
            continue
        introduced = git(view.root, "log", "--diff-filter=A", "--format=%H", candidate, "--", map_path).stdout.split()
        source_revision = introduced[-1] if introduced else candidate
        project = _project_at(view.root, seal.get("reviewed_base", ""))
        errors = mapping_errors(view.root, mapping, seal_raw, project, source_revision)
        if not errors:
            return None
    return ("sealed proof has no trusted integration mapping for this candidate" if found else
            "failed_at historical red commit is unavailable and no trusted proof seal maps it to this candidate")
