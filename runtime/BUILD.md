These files are the small Beholder 3 runtime bridge used by the English-overwrite patch. They are developer inputs, not player prerequisites. Players use the release installer and need none of the tools below.

The source does not add a locale or provider, inject dialogue data, poll scenes, enumerate text objects, or hook object creation. Managed strings use the original assembly digest, MVID, method token, raw IL digest, opcode sequence, instruction ordinal, and original operand guards. Font support installs a TMP fallback and handles individual legacy text components through enable, text/font setter, and mesh-building hooks. The font setter hook has an explicit re-entry guard. It does not edit text or layout.

Inputs

- The canonical `parr0t-release-checkpoint.json` from this release is the sole target-text input. Do not create a second translation export.
- The supported player's original `HDRP` and `URP` managed assemblies supply metadata and compiler references. Their exact hashes are listed in `runtime-build-inputs.json`. Original game files and extracted source text are not repository inputs.
- Use the unmodified BepInEx Windows x64 5.4.23.5 core files declared in `third-party-runtime-inputs.json`.
- Use the declared Microsoft .NET Framework C# compiler for the original compile recipe. The recipe records its hash, version, reference hashes, flags, source hashes, and the exact published output hashes.
- Python 3 and PowerShell 7 are developer tools for the metadata-only bridge. The font bundle recipe additionally uses UnityPy 1.23.0 and lz4 4.4.5. The selected Parr0t Unity SDK reference is `2826c6624cb52dff6d20050838d753d00a3e2dd6`; no SDK tree is copied here.

Managed mapping and compilation

`managed-callsite-bindings.json` contains only stable IDs and source/assembly/method fingerprints for the 338 guarded call sites. The bridge reads the original assembly as PE metadata; it does not load or execute a game assembly. Temporary metadata output is confined to a temporary build directory and is not a repository file.

From an arbitrary directory, supply paths of your choice:

```text
python -B runtime/build-runtime.py --checkpoint parr0t-release-checkpoint.json --checkpoint-sha256 CHECKPOINT_SHA256 --game ORIGINAL_GAME_DIRECTORY --loader-core BEPINEX_CORE_DIRECTORY --compiler CSC_EXECUTABLE --output BUILD_DIRECTORY
```

This produces the two managed mapping files, required-character files, and four plugin DLLs. `PayloadBinding.cs` is generated from the mapping digest. The mapping header binds the canonical checkpoint SHA-256 declared in the binding file. Its map digest determines the generated PayloadBinding.cs guard. The resulting mapping digest must equal the corresponding released-file digest in `runtime-build-inputs.json`.

For a read-only comparison with an extracted release's `payload` directory, use `--verify-existing PAYLOAD_DIRECTORY` instead of `--output`, `--compiler`, and `--loader-core`. This compares generated mappings in memory without writing a replacement payload or compiling DLLs.

The original DLL compilation did **not** enable deterministic compilation. Recompilation may change PE timestamps and module identifiers. The published DLLs are the original, exact tested outputs declared by hash; binary reproducibility is not claimed. Do not substitute a fresh compile for a verified release asset without validating and declaring a new release.

Font bundle

`build-font-bundle.py` reproduces the title-specific three-object container: a licensed, unmodified Noto Sans CJK KR Regular 2.004 font, an owned blank 128-by-128 atlas, and an owned bundle manifest. The original files named by the declared template inputs supply native format schemas only. The recipe replaces every object value, clears external references and script types, and copies no original font, texture pixels, shader, or game object values.

```text
python -B runtime/build-font-bundle.py --font NotoSansCJKkr-Regular.otf --font-template ORIGINAL_SHAREDASSETS0 --bundle-template ORIGINAL_STRINGTABLES_BUNDLE --output BUILD_DIRECTORY/korean-font.bundle
```

The recipe checks all input hashes and the expected output digest. `--verify-existing EXISTING_FONT_BUNDLE` replaces `--output` for an in-memory comparison. It never writes to the original game. The original font, its OFL notice, and loader licenses/source are declared in `third-party-runtime-inputs.json` and accompany the release. Retain the exact `font-NOTICE.txt` and `OFL.txt` declared by the released-file hashes.

All paths above are developer-selected inputs or relative output paths. No build-host path is required by the player or embedded in the recipe.
