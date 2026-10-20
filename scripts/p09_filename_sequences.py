"""Recover original K-Fashion filenames, which metadata image-ID paths omit."""
import argparse
import hashlib
import json
import zipfile
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from scripts.kfashion_common import derive_look_group, parse_image_name
from scripts.p09_group_candidates import read_csv, sha256, verify_audit_lock, write_csv, write_json


def extract_sequences(rows, label_zip):
    records = []
    groups = defaultdict(list)
    with zipfile.ZipFile(label_zip) as archive:
        for row in sorted((r for r in rows if r['label'] == '1'), key=lambda r: r['image_id']):
            member = f"{row['style']}/{row['image_id']}.json"
            raw = archive.read(member)
            name = parse_image_name(json.loads(raw))
            if not name:
                raise ValueError(f'missing original filename: {member}')
            group = derive_look_group(name)
            records.append(dict(image_id=row['image_id'], label_member=member,
                                label_sha256=hashlib.sha256(raw).hexdigest(), original_filename=name,
                                filename_group=group, existing_group=row['look_group']))
            if group:
                groups[(row['source_domain'], group)].append(row['image_id'])
    pairs = [dict(a=a, b=b, filename_group=group)
             for (_, group), ids in sorted(groups.items()) for a, b in combinations(ids, 2)]
    return records, pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label-zip', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('output exists; never overwrite')
    verified = verify_audit_lock('experiments/p08_anonymized/leakage_audit/audit_lock.json')
    rows = read_csv('data/metadata.csv')
    records, pairs = extract_sequences(rows, args.label_zip)
    args.out.mkdir(parents=True)
    write_csv(args.out/'filename_provenance.csv', records, list(records[0]))
    write_csv(args.out/'filename_candidates.csv', pairs, ['a', 'b', 'filename_group'])
    by_id = {r['image_id']: r for r in rows}
    summary = dict(real_images=len(records), filename_group_images=sum(bool(r['filename_group']) for r in records),
                   filename_pairs=len(pairs), pairs_outside_existing_group=sum(by_id[r['a']]['look_group'] != by_id[r['b']]['look_group'] for r in pairs))
    write_json(args.out/'summary.json', summary)
    write_json(args.out/'input_lock.json', dict(verified_audit_files=verified, label_zip_sha256=sha256(args.label_zip),
                source_sha256=sha256(__file__), filename_rule_sha256=sha256('scripts/kfashion_common.py'),
                outputs_sha256={p.name: sha256(p) for p in args.out.iterdir()}))
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
