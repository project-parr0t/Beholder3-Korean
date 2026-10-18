"""Build only the three-object, licensed-font-owned bundle for this title.

Original game files supply native format schemas only; every object value is
replaced below. This script never writes the game or reads its raster pixels.
"""
import argparse,copy,hashlib,json,struct
from pathlib import Path
import UnityPy as u
parser=argparse.ArgumentParser();parser.add_argument('--font',type=Path,required=True);parser.add_argument('--font-template',type=Path,required=True);parser.add_argument('--bundle-template',type=Path,required=True);parser.add_argument('--output',type=Path);parser.add_argument('--verify-existing',type=Path);args=parser.parse_args()
assert bool(args.output)!=bool(args.verify_existing)
inputs=json.loads((Path(__file__).parent/'runtime-build-inputs.json').read_text())['font_bundle']
assert u.__version__==inputs['parser_version']
for row in inputs['template_inputs']:assert hashlib.sha256(getattr(args,row['argument']).read_bytes()).hexdigest()==row['sha256']
font_data=args.font.read_bytes();assert hashlib.sha256(font_data).hexdigest()==inputs['source_font']['sha256']
U16=lambda b,o:struct.unpack_from('>H',b,o)[0]
U32=lambda b,o:struct.unpack_from('>I',b,o)[0]
tables={font_data[12+i*16:16+i*16].decode('ascii'):U32(font_data,20+i*16)for i in range(U16(font_data,4))}
hhea=tables['hhea'];metrics={'units_per_em':U16(font_data,tables['head']+18),'ascender':struct.unpack_from('>h',font_data,hhea+4)[0],'descender':struct.unpack_from('>h',font_data,hhea+6)[0],'line_gap':struct.unpack_from('>h',font_data,hhea+8)[0]}
# Only native Font, Texture2D and AssetBundle metadata types are reused; no original object values survive.
e=u.Environment();f=e.load_file(str(args.font_template));native=f.objects[133];font_type=copy.copy(native.serialized_type);font_type.node=native._get_typetree_node();font_type.type_dependencies=();
for ix,node in enumerate(font_type.node.traverse()):
 for key in ['m_TypeFlags','m_VariableCount','m_MetaFlag','m_RefTypeHash']:
  if getattr(node,key) is None:setattr(node,key,0)
 if node.m_Index is None:node.m_Index=ix
e2=u.Environment();bundle=e2.load_file(str(args.bundle_template));manifest=next(o for o in e2.objects if o.type.name=='AssetBundle');sf=manifest.assets_file
manifest_type=copy.copy(manifest.serialized_type);manifest_type.node=manifest._get_typetree_node();manifest_type.type_dependencies=()
font_obj=native;font_obj.assets_file=sf;font_obj.path_id=2;font_obj.type_id=0;font_obj.serialized_type=font_type
manifest.path_id=1;manifest.type_id=1;manifest.serialized_type=manifest_type
from UnityPy.helpers.Tpk import get_typetree_node
from UnityPy.enums import ClassIDType
texture_type=copy.copy(next(t for t in f.types if t.class_id==28));texture_type.node=get_typetree_node(28,sf.version);texture_type.type_dependencies=()
for ix,node in enumerate(texture_type.node.traverse()):
 for key in ['m_TypeFlags','m_VariableCount','m_MetaFlag','m_RefTypeHash']:
  if getattr(node,key) is None:setattr(node,key,0)
 if node.m_Index is None:node.m_Index=ix
texture_obj=object.__new__(type(font_obj));texture_obj.__dict__.update(font_obj.__dict__);texture_obj.assets_file=sf;texture_obj.path_id=3;texture_obj.type_id=2;texture_obj.class_id=28;texture_obj.type=ClassIDType.Texture2D;texture_obj.serialized_type=texture_type
def empty(node):
 if node.m_Type=='string':return ''
 if node.m_Children and node.m_Children[0].m_Type=='Array':return []
 if node.m_Type in ['float','double']:return 0.0
 if node.m_Type=='bool':return False
 if not node.m_Children:return 0
 return {c.m_Name:empty(c) for c in node.m_Children}
texture_fields=empty(texture_type.node)
texture_fields.update({'m_Name':'Parr0t Korean Dynamic Atlas','m_Width':128,'m_Height':128,'m_CompleteImageSize':16384,'m_TextureFormat':1,'m_MipCount':1,'m_IsReadable':True,'m_ImageCount':1,'m_TextureDimension':2,'m_ColorSpace':1,'image data':bytes(16384)})
texture_fields['m_TextureSettings'].update({'m_FilterMode':1,'m_Aniso':1,'m_WrapU':1,'m_WrapV':1,'m_WrapW':1})

sf.types=[font_type,manifest_type,texture_type];sf.script_types=[];sf.externals=[];sf.ref_types=[];sf.userInformation='';sf.objects={1:manifest,2:font_obj,3:texture_obj};sf._enable_type_tree=True;sf._cache={}
font_fields={'m_Name':'Parr0t Korean Font','m_LineSpacing':16*(metrics['ascender']-metrics['descender']+metrics['line_gap'])/metrics['units_per_em'],'m_DefaultMaterial':{'m_FileID':0,'m_PathID':0},'m_FontSize':16.0,'m_Texture':{'m_FileID':0,'m_PathID':3},'m_AsciiStartOffset':0,'m_Tracking':1.0,'m_CharacterSpacing':0,'m_CharacterPadding':1,'m_ConvertCase':-2,'m_CharacterRects':[],'m_KerningValues':[],'m_PixelScale':0.1,'m_FontData':list(font_data),'m_Ascent':16*metrics['ascender']/metrics['units_per_em'],'m_Descent':16*metrics['descender']/metrics['units_per_em'],'m_DefaultStyle':0,'m_FontNames':['Noto Sans CJK KR'],'m_FallbackFonts':[],'m_FontRenderingMode':0,'m_UseLegacyBoundsCalculation':False,'m_ShouldRoundAdvanceValue':True}
manifest_fields={'m_Name':'parr0t-korean-font','m_PreloadTable':[{'m_FileID':0,'m_PathID':2},{'m_FileID':0,'m_PathID':3}],'m_Container':[('parr0t-korean-font',{'preloadIndex':0,'preloadSize':2,'asset':{'m_FileID':0,'m_PathID':2}}),('parr0t-korean-atlas',{'preloadIndex':1,'preloadSize':1,'asset':{'m_FileID':0,'m_PathID':3}})],'m_MainAsset':{'preloadIndex':0,'preloadSize':1,'asset':{'m_FileID':0,'m_PathID':2}},'m_RuntimeCompatibility':1,'m_AssetBundleName':'parr0t-korean-font','m_Dependencies':[],'m_IsStreamedSceneAssetBundle':False,'m_ExplicitDataLayout':1,'m_PathFlags':0,'m_SceneHashes':[]}
font_obj.save_typetree(font_fields);texture_obj.save_typetree(texture_fields);manifest.save_typetree(manifest_fields);sf.name='CAB-parr0t-korean-font';bundle.files={'CAB-parr0t-korean-font':sf}
payload=bundle.save(packer='lz4')
assert len(payload)==inputs['result_bytes'] and hashlib.sha256(payload).hexdigest()==inputs['result_sha256']
if args.verify_existing:assert args.verify_existing.read_bytes()==payload
else:args.output.write_bytes(payload)
print('Licensed font bundle digest verified; no proprietary object values retained.')
