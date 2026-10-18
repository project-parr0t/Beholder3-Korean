# Native replacement recipe

Use Python 3.13 with the published `sdk-unity-2021.1` SDK commit declared in
`native-build.json`, and its exact `requirements-unity.txt` dependencies.
The canonical release checkpoint is the sole translation source. No private
inventory, model record, extracted source-text export, or copied SDK is required.

Supply a pristine copy of the supported Windows game build. The program verifies
every declared original-file digest before generating new files, reads managed
assemblies as metadata only, and never writes inside the supplied game folder.
It derives literal locations from checkpoint IDs and table identities from the
original serialized table/shared-data references. Other table locales, control
data, and untouched object bytes are preserved. Catalog CRC, size, and cache
identities are recomputed with the SDK and checked against the declared outputs.

```text
python build_native.py --original-game <original-game-folder> --checkpoint <parr0t-release-checkpoint.json> --output <new-output-folder>
```

`--only <relative-path>` can be repeated to rebuild declared outputs selectively.
Every generated native file must match the release recipe's exact digest. This
program does not install a patch or launch the game. Runtime components and the
standard installer are assembled separately; do not distribute original game
assemblies or build dependencies with the patch.
