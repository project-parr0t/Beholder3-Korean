using System;
using System.IO;
using BepInEx;
using Parr0t.PrivateFontPreparation;

namespace Parr0t.PrivateFontBootstrap
{
    [BepInPlugin("parr0t.private.ko-font-support", "Parr0t Korean Font Support", "0.1.0")]
    [BepInProcess("Beholder3.exe")]
    public sealed class FontPlugin : BaseUnityPlugin
    {
        private KoreanFontSupport support;
        private void Awake()
        {
            if (!UnityEngine.Application.unityVersion.StartsWith("2021.1.", StringComparison.Ordinal))
                throw new InvalidOperationException("FONT_UNSUPPORTED_UNITY_VERSION");
            string directory = Path.GetDirectoryName(Info.Location);
            string bundle = Path.Combine(directory, "korean-font.bundle");
            string characters = File.ReadAllText(Path.Combine(directory, "required-characters.txt"));
            support = new KoreanFontSupport();
            support.Initialize(bundle, characters);
            FontRendererHooks.Initialize(support);
            Logger.LogInfo("FONT_SUPPORT_INITIALIZED");
        }
    }
}
