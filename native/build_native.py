"""Build the title's native replacements from original files and one checkpoint."""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path, PurePosixPath

import UnityPy
from game_l10n.release_checkpoint import canonical_checkpoint_bytes, validate_release_checkpoint
from game_l10n.unity import require_dependencies
from game_l10n.unity.catalog import patch_catalog
from game_l10n.unity.schema import ManagedSchemas
from game_l10n.unity.serialization import read_complete_typetree, rewrite_fields, rewrite_registry_fields


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(root, value):
    p=PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or ':' in value:
        raise ValueError('unsafe_relative_input')
    result=(root/str(p)).resolve()
    result.relative_to(root.resolve())
    return result


def field_path(tree, pointer):
    path=[]
    current=tree
    for part in pointer.lstrip('/').split('/'):
        key=int(part) if isinstance(current,list) else part
        current=current[key]
        path.append(key)
    if not isinstance(current,str):
        raise ValueError('checkpoint_binding_is_not_string')
    return path,current


def literal_binding(ident):
    parts=ident.split(':',5)
    if len(parts)!=6 or parts[:2]!=['unity','literal']:
        raise ValueError('unsupported_native_identity')
    return parts[2],parts[3],int(parts[4]),parts[5]


def table_identity(table, owner, index):
    ref=table['m_SharedData']
    if ref['m_FileID']==0:
        asset=owner.assets_file.name
    else:
        asset=owner.assets_file.externals[ref['m_FileID']-1].path.replace('\\','/').rsplit('/',1)[-1]
    shared=index[(asset,ref['m_PathID'])]
    return read_complete_typetree(shared)['m_TableCollectionNameGuidString']


def object_edits(obj, replacements):
    node=obj._get_typetree_node()
    try:
        return rewrite_fields(obj,node,replacements)
    except ValueError:
        if not any(n.m_Type=='ManagedReferencesRegistry' for n in node.traverse()):
            raise
        return rewrite_registry_fields(obj,node,replacements)


def rebuild_asset(relative, original, checkpoint, bindings):
    variant=relative.split('/')[0]
    managed=original/variant/'Beholder3_Data/Managed'
    schemas=ManagedSchemas('2021.1.0f1',[managed],[original])
    env=UnityPy.Environment()
    source=safe_path(original,relative)
    before=source.read_bytes()
    if digest(before)!=bindings[relative]['sha256']:
        raise ValueError('original_source_binding_mismatch')
    container=env.load_file(before,name=Path(relative).name)
    owned={(o.assets_file.name,o.path_id):o for o in env.objects}
    unchanged={key:o.get_raw_data() for key,o in owned.items()}
    if relative.endswith('.bundle'):
        shared=relative.replace('localization-stringtables','localization-assets-shared')
        raw=safe_path(original,shared).read_bytes()
        if digest(raw)!=bindings[shared]['sha256']:
            raise ValueError('original_shared_binding_mismatch')
        env.load_file(raw,name=Path(shared).name)
    elif Path(relative).name!='globalgamemanagers.assets':
        dependency=variant+'/Beholder3_Data/globalgamemanagers.assets'
        raw=safe_path(original,dependency).read_bytes()
        if digest(raw)!=bindings[dependency]['sha256']:
            raise ValueError('original_script_binding_mismatch')
        env.load_file(raw,name='globalgamemanagers.assets')
    env.typetree_generator=schemas
    index={(o.assets_file.name,o.path_id):o for o in env.objects}
    changes={}
    count=0
    if relative.endswith('.bundle'):
        tables={e['id']:e for e in checkpoint['entries'] if e['id'].startswith('unity:string_table:')}
        for key,obj in owned.items():
            tree=read_complete_typetree(obj)
            if tree.get('m_LocaleId',{}).get('m_Code')!='en':
                continue
            guid=table_identity(tree,obj,index)
            edits=[]
            for n,row in enumerate(tree['m_TableData']):
                ident='unity:string_table:'+guid+':'+str(row['m_Id'])
                if ident not in tables:
                    continue
                entry=tables[ident]
                if digest(row['m_Localized'].encode())!=entry['source_sha256']:
                    raise ValueError('original_table_source_mismatch')
                edits.append({'path':['m_TableData',n,'m_Localized'],'source':row['m_Localized'],'text':entry['target']})
                count+=1
            if edits:
                changes[key]=object_edits(obj,edits)
                obj.set_raw_data(changes[key])
        if count!=len(tables):
            raise ValueError('checkpoint_table_binding_incomplete')
    else:
        grouped=defaultdict(list)
        for entry in checkpoint['entries']:
            if not entry['id'].startswith('unity:literal:'):
                continue
            rel,serialized,pid,pointer=literal_binding(entry['id'])
            if rel==relative:
                grouped[(serialized,pid)].append((entry,pointer))
        for key,entries in grouped.items():
            obj=owned[key]
            tree=read_complete_typetree(obj)
            edits=[]
            for entry,pointer in entries:
                path,value=field_path(tree,pointer)
                if digest(value.encode())!=entry['source_sha256']:
                    raise ValueError('original_literal_source_mismatch')
                edits.append({'path':path,'source':value,'text':entry['target']})
                count+=1
            changes[key]=object_edits(obj,edits)
            obj.set_raw_data(changes[key])
    rebuilt=container.save()
    checked=UnityPy.Environment()
    checked.load_file(rebuilt,name=Path(relative).name)
    actual={(o.assets_file.name,o.path_id):o.get_raw_data() for o in checked.objects}
    if set(actual)!=set(unchanged) or any(actual[k]!=changes.get(k,v) for k,v in unchanged.items()):
        raise ValueError('unmodified_object_bytes_changed')
    schemas.verify_unchanged()
    if digest(source.read_bytes())!=bindings[relative]['sha256']:
        raise ValueError('original_source_changed')
    return rebuilt,count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-game',required=True,type=Path)
    parser.add_argument('--checkpoint',required=True,type=Path)
    parser.add_argument('--recipe',type=Path,default=Path(__file__).with_name('native-build.json'))
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--only',action='append',help='Exact relative output path; repeat to narrow the rebuild')
    args=parser.parse_args()
    require_dependencies()
    original=args.original_game.resolve()
    output=args.output.resolve()
    if output.exists() or output.is_relative_to(original) or original.is_relative_to(output):
        raise ValueError('new_output_outside_original_required')
    recipe=json.loads(args.recipe.read_text(encoding='utf-8'))
    raw=args.checkpoint.read_bytes()
    checkpoint=validate_release_checkpoint(json.loads(raw),expected_patch_id=recipe['patch_id'],expected_release_id=recipe['release_id'])
    if digest(raw)!=recipe['checkpoint_sha256'] or canonical_checkpoint_bytes(checkpoint)!=raw:
        raise ValueError('canonical_checkpoint_mismatch')
    if checkpoint['sdk']['commit']!=recipe['sdk_commit'] or any(e['status']!='reviewed' for e in checkpoint['entries']):
        raise ValueError('checkpoint_sdk_or_review_mismatch')
    bindings={b['path']:b for b in recipe['original_files']}
    for rel,b in bindings.items():
        source=safe_path(original,rel)
        if source.stat().st_size!=b['bytes'] or digest(source.read_bytes())!=b['sha256']:
            raise ValueError('unsupported_original_game_build')
    wanted=set(args.only) if args.only else {f['path'] for f in recipe['native_outputs']}
    if not wanted<={f['path'] for f in recipe['native_outputs']}:
        raise ValueError('undeclared_native_output')
    pending={f['path']:f for f in recipe['native_outputs'] if f['path'] in wanted}
    built={}
    output.mkdir(parents=True)
    for rel,expected in sorted(pending.items(),key=lambda p:p[0].endswith('/catalog.json')):
        if rel.endswith('/catalog.json'):
            bundle=next(f['path'] for f in recipe['native_outputs'] if f['path'].startswith(rel.split('/')[0]+'/') and f['path'].endswith('.bundle'))
            rawbundle=built[bundle] if bundle in built else rebuild_asset(bundle,original,checkpoint,bindings)[0]
            raw,_=patch_catalog(safe_path(original,rel).read_bytes(),Path(bundle).name,rawbundle)
        else:
            raw,_=rebuild_asset(rel,original,checkpoint,bindings)
        if len(raw)!=expected['bytes'] or digest(raw)!=expected['sha256']:
            raise ValueError('rebuilt_native_output_digest_mismatch')
        destination=safe_path(output,rel)
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(raw)
        built[rel]=raw
    print(json.dumps({'status':'verified','native_files':len(built),'checkpoint_sha256':recipe['checkpoint_sha256']}))


if __name__=='__main__':
    main()
