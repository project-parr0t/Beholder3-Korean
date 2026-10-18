using System;using System.Collections.Generic;using System.Reflection;using HarmonyLib;using TMPro;using UnityEngine.Localization.Settings;
namespace Parr0t.PrivateManagedLiterals {
 internal sealed class ReportNameValue {internal readonly string SourceHash,Target;internal ReportNameValue(string hash,string target){SourceHash=hash;Target=target;}}
 internal static class ReportNameSupport {
  static FieldInfo npcsField,dropdownField,keyField;static Harmony hook;
  internal static void Initialize(){
   if(hook!=null)return;
   Type owner=AccessTools.TypeByName("Beholder3.UI.FormScreen");if(owner==null||owner.Assembly.GetName().Name!=ReportNameValues.AssemblyName)throw new InvalidOperationException("REPORT_NAME_OWNER_BINDING");
   MethodInfo method=owner.GetMethod("FillNPCDropdown",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.DeclaredOnly);
   if(method==null||method.MetadataToken!=ReportNameValues.MethodToken||method.ReturnType!=typeof(void)||method.GetParameters().Length!=0||LiteralEngine.Hash(method.GetMethodBody().GetILAsByteArray())!=ReportNameValues.MethodHash)throw new InvalidOperationException("REPORT_NAME_METHOD_BINDING");
   npcsField=AccessTools.Field(owner,"npcs");dropdownField=AccessTools.Field(owner,"npcDropdown");if(npcsField==null||dropdownField==null||!npcsField.FieldType.IsArray||dropdownField.FieldType!=typeof(TMP_Dropdown))throw new InvalidOperationException("REPORT_NAME_FIELD_BINDING");
   Type npc=npcsField.FieldType.GetElementType();if(npc.FullName!="Beholder3.NPCs.Data.NPC")throw new InvalidOperationException("REPORT_NAME_KEY_OWNER_BINDING");keyField=AccessTools.Field(npc,"characterKey");if(keyField==null||!keyField.FieldType.IsEnum)throw new InvalidOperationException("REPORT_NAME_KEY_BINDING");
   hook=new Harmony("parr0t.private.ko-report-name-render");try{hook.Patch(method,postfix:new HarmonyMethod(typeof(ReportNameSupport),"AfterFill"));}catch{hook.UnpatchSelf();hook=null;throw;}
  }
  internal static void Stop(){if(hook!=null){hook.UnpatchSelf();hook=null;}}
  static void AfterFill(object __instance){
   var locale=LocalizationSettings.SelectedLocale;if(locale==null)return;string code=locale.Identifier.Code;bool english=String.Equals(code,"en",StringComparison.OrdinalIgnoreCase)||code.StartsWith("en-",StringComparison.OrdinalIgnoreCase);if(!english)return;
   var npcs=npcsField.GetValue(__instance)as Array;var dropdown=dropdownField.GetValue(__instance)as TMP_Dropdown;if(npcs==null||dropdown==null||dropdown.options==null||dropdown.options.Count!=npcs.Length+1)return;
   var keys=new string[npcs.Length];for(int i=0;i<keys.Length;i++){object npc=npcs.GetValue(i);if(npc!=null)keys[i]=Convert.ToString(keyField.GetValue(npc),System.Globalization.CultureInfo.InvariantCulture);}
   if(ApplyLabels(keys,dropdown.options,true)>0)dropdown.RefreshShownValue();
  }
  internal static int ApplyLabels(string[] keys,IList<TMP_Dropdown.OptionData> options,bool english){
   if(!english||keys==null||options==null||options.Count!=keys.Length+1)return 0;int changed=0;
   for(int i=0;i<keys.Length;i++){ReportNameValue value;if(keys[i]==null||!ReportNameValues.Names.TryGetValue(keys[i],out value))continue;var option=options[i+1];if(option==null||option.text==value.Target)continue;
    if(LiteralEngine.Hash(System.Text.Encoding.UTF8.GetBytes(option.text??String.Empty))!=value.SourceHash)continue;option.text=value.Target;changed++;
   }return changed;
  }
 }
}
