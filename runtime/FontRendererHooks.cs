using System;using HarmonyLib;using UnityEngine.UI;
namespace Parr0t.PrivateFontPreparation {
 public static class FontRendererHooks {
  static KoreanFontSupport current;static bool applying;static Harmony harmony;
  public static void Initialize(KoreanFontSupport support){
   if(current!=null)throw new InvalidOperationException("FONT_HOOKS_ALREADY_INITIALIZED");current=support;harmony=new Harmony("parr0t.private.ko-font-support");
   foreach(string method in new[]{"OnEnable","set_text","set_font","OnPopulateMesh"}){
    var target=AccessTools.DeclaredMethod(typeof(Text),method);if(target==null)throw new MissingMethodException("FONT_RENDERER_API_"+method);
    var hook=new HarmonyMethod(typeof(FontRendererHooks),"Apply");
    if(method=="OnPopulateMesh")harmony.Patch(target,prefix:hook);else harmony.Patch(target,postfix:hook);
   }
  }
  static void Apply(Text __instance){if(current==null||applying)return;applying=true;try{current.ApplyLegacyFont(__instance);}finally{applying=false;}}
 }
}
