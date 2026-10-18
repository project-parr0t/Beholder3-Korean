"""Title bridge: recover guarded CIL operands from the player's own assembly.

The canonical release checkpoint is the only target-text input. The original
assembly is read as PE metadata, never loaded or executed by this build tool.
"""
import argparse
import hashlib
import json
import pathlib
import struct
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def string(value):
    data = value.encode("utf-8")
    n, prefix = len(data), bytearray()
    while n >= 128:
        prefix.append((n & 127) | 128)
        n >>= 7
    return bytes(prefix + bytes([n])) + data


def run(command):
    subprocess.run([str(x) for x in command], check=True)


def materialize(checkpoint, binding, audit):
    entries = {entry["id"]: entry for entry in checkpoint["entries"]}
    methods = {method["token"]: method for method in audit["methods"]}
    assert audit["mvid"] == binding["mvid"]
    grouped = {}
    for target in binding["targets"]:
        entry = entries[target["id"]]
        assert entry["source_sha256"] == target["source_sha256"]
        assert hashlib.sha256(entry["target"].encode("utf-8")).hexdigest() == entry["target_sha256"]
        method = methods[target["method_token"]]
        assert method["il_sha256"] == target["method_il_sha256"]
        instruction = method["instructions"][target["instruction_ordinal"]]
        assert instruction["offset"] == target["il_offset"] and instruction["opcode"] == 114
        assert hashlib.sha256(instruction["literal"].encode("utf-8")).hexdigest() == target["source_sha256"]
        grouped.setdefault(method["token"], []).append((target, instruction["literal"], entry["target"]))
    header = read(HERE / "managed-callsite-bindings.json")["candidate_header_sha256"]
    output = string("parr0t.managed-literals.v1") + string(header) + struct.pack("<i", 1)
    output += string(binding["assembly_file"]) + string(binding["assembly_sha256"]) + string(binding["mvid"])
    output += struct.pack("<i", len(grouped))
    for token, targets in sorted(grouped.items()):
        method = methods[token]
        instructions = method["instructions"]
        output += struct.pack("<i", token) + string(method["il_sha256"]) + struct.pack("<i", len(instructions))
        output += b"".join(struct.pack("<h", item["opcode"]) for item in instructions)
        output += struct.pack("<i", len(targets))
        for target, source, text in targets:
            output += struct.pack("<i", target["instruction_ordinal"]) + string(source) + string(text)
    return output



def report_values(checkpoint, variant):
    binding = read(HERE / "report-name-bindings.json")
    guard = next(row for row in binding["variants"] if row["variant"] == variant)
    entries = {row["id"]: row for row in checkpoint["entries"]}
    rows = []
    for row in binding["bindings"]:
        entry = entries[row["id"]]
        assert entry["source_sha256"] == row["source_sha256"] and entry["status"] == "reviewed"
        rows.append("{" + json.dumps(row["key"]) + ",new ReportNameValue(" + json.dumps(row["source_sha256"]) + "," + json.dumps(entry["target"], ensure_ascii=True) + ")}")
    return ('namespace Parr0t.PrivateManagedLiterals {internal static class ReportNameValues {internal const string AssemblyName="' + guard["assembly_name"] + '";internal const int MethodToken=' + str(guard["method_token"]) + ';internal const string MethodHash="' + guard["method_sha256"] + '";internal static readonly System.Collections.Generic.Dictionary<string,ReportNameValue> Names=new System.Collections.Generic.Dictionary<string,ReportNameValue>{' + ','.join(rows) + '};}}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=pathlib.Path, required=True)
    parser.add_argument("--checkpoint-sha256", required=True)
    parser.add_argument("--game", type=pathlib.Path, required=True)
    parser.add_argument("--loader-core", type=pathlib.Path)
    parser.add_argument("--compiler", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--verify-existing", type=pathlib.Path)
    parser.add_argument("--powershell", default="pwsh")
    args = parser.parse_args()
    assert digest(args.checkpoint) == args.checkpoint_sha256
    checkpoint = read(args.checkpoint)
    assert checkpoint["schema"] == "parr0t.release-checkpoint/v1"
    assert bool(args.verify_existing) != bool(args.output)
    metadata = read(HERE / "runtime-build-inputs.json")
    assert all(digest(HERE / name) == value for name, value in metadata["source_sha256"].items())
    hangul = "".join(sorted({character for entry in checkpoint["entries"] for character in entry["target"]
                           if 0xAC00 <= ord(character) <= 0xD7A3 or 0x1100 <= ord(character) <= 0x11FF
                           or 0x3130 <= ord(character) <= 0x318F or 0xA960 <= ord(character) <= 0xA97F
                           or 0xD7B0 <= ord(character) <= 0xD7FF}))
    character_records = [item for item in metadata["released_files"] if item["path"].endswith("/required-characters.txt")]
    assert len(character_records) == 2
    assert all(hashlib.sha256(hangul.encode("utf-8")).hexdigest() == item["sha256"] for item in character_records)
    with tempfile.TemporaryDirectory(prefix="beholder3-runtime-metadata-") as temporary:
        for binding in read(HERE / "managed-callsite-bindings.json")["variants"]:
            variant = binding["variant"]
            managed = args.game / variant / "Beholder3_Data" / "Managed"
            assembly = managed / binding["assembly_file"]
            assert digest(assembly) == binding["assembly_sha256"]
            audit_file = pathlib.Path(temporary) / (variant + ".json")
            run([args.powershell, "-NoLogo", "-NoProfile", "-File", HERE / "inspect-managed.ps1", "-Assembly", assembly, "-Output", audit_file])
            data = materialize(checkpoint, binding, read(audit_file))
            relative = pathlib.Path(variant) / "BepInEx/plugins/Parr0tKorean/managed-literals.bin"
            record = next(item for item in metadata["released_files"] if item["path"] == relative.as_posix())
            assert hashlib.sha256(data).hexdigest() == record["sha256"] and len(data) == record["bytes"]
            report_source = report_values(checkpoint, variant)
            report_record = next(row for row in metadata["generated_report_names"] if row["variant"] == variant)
            assert hashlib.sha256(report_source.encode("utf-8")).hexdigest() == report_record["sha256"]
            if args.verify_existing:
                assert (args.verify_existing / relative).read_bytes() == data
                continue
            assert args.compiler and args.loader_core
            assert digest(args.compiler) == metadata["compiler"]["sha256"]
            destination = args.output / variant
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "managed-literals.bin").write_bytes(data)
            (destination / "required-characters.txt").write_text(hangul, encoding="utf-8")
            generated = destination / "PayloadBinding.cs"
            generated.write_text('namespace Parr0t.PrivateManagedLiterals { public static class PayloadBinding { public const string Digest="' + hashlib.sha256(data).hexdigest() + '"; } }\n', encoding="utf-8")
            report_generated = destination / "ReportNameValues.cs"
            report_generated.write_text(report_source, encoding="utf-8")
            reference_sets = next(item for item in metadata["variants"] if item["variant"] == variant)["references"]
            for kind, sources, name in [
                ("managed", [HERE / "ManagedLiteralPlugin.cs", generated, HERE / "ReportNameSupport.cs", report_generated], "Parr0t.Korean.ManagedLiterals.dll"),
                ("font", [HERE / "FontPlugin.cs", HERE / "KoreanFontSupport.cs", HERE / "FontRendererHooks.cs"], "Parr0t.Korean.FontSupport.dll"),
            ]:
                references = []
                for filename, expected in reference_sets[kind].items():
                    reference = (args.loader_core if filename in {"BepInEx.dll", "0Harmony.dll"} else managed) / filename
                    assert digest(reference) == expected
                    references.append("/reference:" + str(reference))
                run([args.compiler, *metadata["compiler_flags"], "/out:" + str(destination / name), *references, *sources])
    print("Checkpoint and original-assembly bindings verified. Published DLLs are not claimed byte-reproducible.")


if __name__ == "__main__":
    main()
