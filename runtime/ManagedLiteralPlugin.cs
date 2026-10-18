using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using System.Security.Cryptography;
#if !SYNTHETIC
using BepInEx;
#endif
using HarmonyLib;

namespace Parr0t.PrivateManagedLiterals {
    public sealed class LiteralTarget { public int Ordinal; public string Source; public string Text; }
    public sealed class MethodPlan { public int Token; public string Hash; public short[] Opcodes; public List<LiteralTarget> Targets = new List<LiteralTarget>(); }
    public sealed class AssemblyPlan { public string File; public string Hash; public string Mvid; public List<MethodPlan> Methods = new List<MethodPlan>(); }
    public static class LiteralEngine {
        static readonly Dictionary<MethodBase, MethodPlan> plans = new Dictionary<MethodBase, MethodPlan>();
        public static string Hash(byte[] bytes) { using(var h=SHA256.Create()) return BitConverter.ToString(h.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant(); }
        // HarmonyX expands short branch encodings without changing instruction order or branch targets.
        public static short CanonicalOpcode(short opcode) { if(opcode>=0x2b&&opcode<=0x37)return (short)(opcode+13);if(opcode==0xde)return 0xdd;return opcode; }
        public static List<AssemblyPlan> Read(string path, string expected) {
            byte[] data=File.ReadAllBytes(path); if(Hash(data)!=expected)throw new InvalidDataException("MANAGED_PAYLOAD_DIGEST");
            var result=new List<AssemblyPlan>(); using(var b=new BinaryReader(new MemoryStream(data),Encoding.UTF8)) {
                if(b.ReadString()!="parr0t.managed-literals.v1")throw new InvalidDataException("MANAGED_PAYLOAD_SCHEMA");
                string candidate=b.ReadString(); if(candidate.Length!=64)throw new InvalidDataException("MANAGED_CANDIDATE_BINDING");
                int n=b.ReadInt32(); if(n!=1)throw new InvalidDataException("MANAGED_ASSEMBLY_COUNT");
                for(int i=0;i<n;i++) { var a=new AssemblyPlan { File=b.ReadString(),Hash=b.ReadString(),Mvid=b.ReadString() };
                    if(Path.GetFileName(a.File)!=a.File||!a.File.EndsWith(".dll",StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("MANAGED_PATH");
                    int nm=b.ReadInt32(); if(nm<=0||nm>10000)throw new InvalidDataException("MANAGED_METHOD_COUNT");
                    for(int j=0;j<nm;j++) { var m=new MethodPlan { Token=b.ReadInt32(),Hash=b.ReadString() }; int no=b.ReadInt32();if(no<=0||no>1000000)throw new InvalidDataException("MANAGED_IL_COUNT");m.Opcodes=new short[no];for(int k=0;k<no;k++)m.Opcodes[k]=b.ReadInt16();
                        int nt=b.ReadInt32();if(nt<=0||nt>no)throw new InvalidDataException("MANAGED_TARGET_COUNT");var seen=new HashSet<int>();for(int k=0;k<nt;k++){var t=new LiteralTarget{Ordinal=b.ReadInt32(),Source=b.ReadString(),Text=b.ReadString()};if(t.Ordinal<0||t.Ordinal>=no||!seen.Add(t.Ordinal)||m.Opcodes[t.Ordinal]!=OpCodes.Ldstr.Value)throw new InvalidDataException("MANAGED_TARGET_IDENTITY");m.Targets.Add(t);}a.Methods.Add(m);
                    } result.Add(a);
                } if(b.BaseStream.Position!=b.BaseStream.Length)throw new InvalidDataException("MANAGED_PAYLOAD_TRAILING_DATA");
            } return result;
        }
        public static List<CodeInstruction> Rewrite(IEnumerable<CodeInstruction> input, MethodPlan plan) {
            var codes=input.ToList(); if(codes.Count!=plan.Opcodes.Length)throw new InvalidOperationException("MANAGED_INSTRUCTION_COUNT");
            for(int i=0;i<codes.Count;i++)if(CanonicalOpcode(codes[i].opcode.Value)!=CanonicalOpcode(plan.Opcodes[i]))throw new InvalidOperationException("MANAGED_OPCODE_IDENTITY");
            foreach(var t in plan.Targets)if(codes[t.Ordinal].opcode!=OpCodes.Ldstr||!(codes[t.Ordinal].operand is string)||!String.Equals((string)codes[t.Ordinal].operand,t.Source,StringComparison.Ordinal))throw new InvalidOperationException("MANAGED_LITERAL_IDENTITY");
            foreach(var t in plan.Targets)codes[t.Ordinal].operand=t.Text;return codes;
        }
        public static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> instructions, MethodBase __originalMethod) { return Rewrite(instructions,plans[__originalMethod]); }
        public static int Apply(string managedDirectory, List<AssemblyPlan> assemblies) {
            var pending=new List<KeyValuePair<MethodBase,MethodPlan>>();
            foreach(var ap in assemblies) { string path=Path.Combine(managedDirectory,ap.File);if(Hash(File.ReadAllBytes(path))!=ap.Hash)throw new InvalidOperationException("MANAGED_ASSEMBLY_DIGEST");
                Assembly a=AppDomain.CurrentDomain.GetAssemblies().FirstOrDefault(x=>!x.IsDynamic&&String.Equals(x.Location,path,StringComparison.OrdinalIgnoreCase));
                if(a==null)a=Assembly.LoadFrom(path);if(!String.Equals(Path.GetFullPath(a.Location),Path.GetFullPath(path),StringComparison.OrdinalIgnoreCase)||Hash(File.ReadAllBytes(a.Location))!=ap.Hash)throw new InvalidOperationException("MANAGED_LOADED_ASSEMBLY_BINDING");if(!String.Equals(a.ManifestModule.ModuleVersionId.ToString(),ap.Mvid,StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("MANAGED_MVID");
                foreach(var mp in ap.Methods) { MethodBase m=a.ManifestModule.ResolveMethod(mp.Token);if(m==null||m.ContainsGenericParameters||m.GetMethodBody()==null||Hash(m.GetMethodBody().GetILAsByteArray())!=mp.Hash)throw new InvalidOperationException("MANAGED_METHOD_IL");
                    var info=Harmony.GetPatchInfo(m);if(info!=null&&info.Transpilers.Count>0)throw new InvalidOperationException("MANAGED_PREEXISTING_TRANSPILER");pending.Add(new KeyValuePair<MethodBase,MethodPlan>(m,mp)); }
            }
            var harmony=new Harmony("parr0t.private.ko-managed-literals");int count=0;
            try { foreach(var pair in pending) { plans.Add(pair.Key,pair.Value);var patch=new HarmonyMethod(typeof(LiteralEngine).GetMethod("Transpiler"));patch.priority=Priority.First;harmony.Patch(pair.Key,transpiler:patch);count+=pair.Value.Targets.Count; } }
            catch { harmony.UnpatchSelf();plans.Clear();throw; } return count;
        }
    }
#if !SYNTHETIC
    [BepInPlugin("parr0t.private.ko-managed-literals", "Parr0t Korean Managed Literals", "0.1.0")]
    [BepInProcess("Beholder3.exe")]
    [BepInDependency("parr0t.private.ko-font-support", BepInDependency.DependencyFlags.HardDependency)]
    public sealed class ManagedLiteralPlugin : BaseUnityPlugin {
        private void OnDestroy() { ReportNameSupport.Stop(); }
        private void Awake() {
            if(!UnityEngine.Application.unityVersion.StartsWith("2021.1.",StringComparison.Ordinal))throw new InvalidOperationException("MANAGED_UNITY_VERSION");
            string dir=Path.GetDirectoryName(Info.Location);var plans=LiteralEngine.Read(Path.Combine(dir,"managed-literals.bin"),PayloadBinding.Digest);
            int count=LiteralEngine.Apply(Path.Combine(UnityEngine.Application.dataPath,"Managed"),plans);
            ReportNameSupport.Initialize();
            Logger.LogInfo("MANAGED_LITERAL_TARGETS_APPLIED="+count);
        }
    }
#endif
}
