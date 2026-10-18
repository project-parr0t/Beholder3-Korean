using System;
using System.IO;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.TextCore.LowLevel;

namespace Parr0t.PrivateFontPreparation
{
    // A verified loader entry must call Initialize on Unity's main thread before localized UI renders.
    // This helper supplies only font assets and renderer reachability. It never changes text or layout.
    public sealed class KoreanFontSupport
    {
        private AssetBundle bundle;
        private TMP_FontAsset fallback;
        private Texture2D legacyAtlas;
        
        public TMP_FontAsset Fallback { get { return fallback; } }
        public Font SourceFont { get; private set; }

        public void Initialize(string bundlePath, string requiredCharacters)
        {
            if (fallback != null) throw new InvalidOperationException("FONT_ALREADY_INITIALIZED");
            if (!File.Exists(bundlePath)) throw new FileNotFoundException("FONT_BUNDLE_MISSING");
            bundle = AssetBundle.LoadFromFile(bundlePath);
            if (bundle == null) throw new InvalidOperationException("FONT_BUNDLE_LOAD_FAILED");
            SourceFont = bundle.LoadAsset<Font>("parr0t-korean-font");
            legacyAtlas = bundle.LoadAsset<Texture2D>("parr0t-korean-atlas");
            if (SourceFont == null || legacyAtlas == null || !SourceFont.dynamic)
                throw new InvalidOperationException("FONT_NATIVE_ASSETS_INVALID");
            fallback = TMP_FontAsset.CreateFontAsset(SourceFont, 90, 9, GlyphRenderMode.SDFAA,
                2048, 2048, AtlasPopulationMode.Dynamic, true);
            if (fallback == null) throw new InvalidOperationException("FONTENGINE_LOAD_FAILED");
            fallback.name = "Parr0t Korean Fallback";
            fallback.hideFlags = HideFlags.DontUnloadUnusedAsset;
            string missing;
            if (!String.IsNullOrEmpty(requiredCharacters) &&
                !fallback.TryAddCharacters(requiredCharacters, out missing, false))
                throw new InvalidOperationException("FONT_REQUIRED_GLYPHS_MISSING");
            if (TMP_Settings.fallbackFontAssets == null)
                throw new InvalidOperationException("FONT_FALLBACK_SETTINGS_UNAVAILABLE");
            if (!TMP_Settings.fallbackFontAssets.Contains(fallback))
                TMP_Settings.fallbackFontAssets.Add(fallback);

        }

        internal void ApplyLegacyFont(Text component)
        {
            if (component == null || component.font == SourceFont || !ContainsHangul(component.text)) return;
            if (SourceFont.material == null)
            {
                Font donor = component.font;
                if (donor == null || donor.material == null)
                    throw new InvalidOperationException("FONT_LEGACY_MATERIAL_DONOR_MISSING");
                Material material = new Material(donor.material);
                material.name = "Parr0t Korean Legacy Font Material";
                material.mainTexture = legacyAtlas;
                SourceFont.material = material;
            }
            component.font = SourceFont;
            component.SetAllDirty();
        }

        private static bool ContainsHangul(string text)
        {
            if (String.IsNullOrEmpty(text)) return false;
            foreach (char c in text)
                if ((c >= '\uAC00' && c <= '\uD7A3') || (c >= '\u1100' && c <= '\u11FF') ||
                    (c >= '\u3130' && c <= '\u318F') || (c >= '\uA960' && c <= '\uA97F') ||
                    (c >= '\uD7B0' && c <= '\uD7FF')) return true;
            return false;
        }
    }

}
