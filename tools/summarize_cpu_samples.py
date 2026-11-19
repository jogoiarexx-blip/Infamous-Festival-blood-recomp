from pathlib import Path
from collections import Counter,defaultdict
from bisect import bisect_right
import re,sys

import argparse
parser=argparse.ArgumentParser(description='Summarize raw PS3_SAMPLE_RVAS using the map from the same executable.')
parser.add_argument('samples', type=Path)
parser.add_argument('linker_map', type=Path)
args=parser.parse_args()

text=args.linker_map.read_text(errors='replace')
base=int(re.search(r'Preferred load address is ([0-9a-fA-F]+)',text)[1],16)
symbols=defaultdict(list)
for line in text.splitlines():
 m=re.match(r'\s+0001:[0-9a-fA-F]+\s+(\S+)\s+([0-9a-fA-F]{16})\s+(.*)',line)
 if m:symbols[int(m[2],16)-base].append((m[1],m[3]))
addresses=sorted(symbols)
if not addresses:
 parser.error('the linker map has no code symbols in section 0001')
blocks=[];rows=[]
for line in args.samples.read_text().splitlines():
 if line.startswith('#'):
  if rows:blocks.append(rows);rows=[]
 elif line.strip():rows.append(int(line,16))
if rows:blocks.append(rows)
for i,block in enumerate(blocks):
 counts=Counter();outside=0
 for addr in block:
  if addr==0:outside+=1;continue
  pos=bisect_right(addresses,addr)-1
  if pos<0:counts['before symbols']+=1;continue
  alias=symbols[addresses[pos]]
  key=' | '.join(a for a,_ in alias[:3])
  if len(alias)>1:key+=f' ({len(alias)} aliases)'
  counts[key]+=1
 print(f'block {i} (nearest linker symbols, aliases grouped): {len(block)} samples, {outside} outside executable')
 for name,n in counts.most_common(10):print(f' {n/len(block):6.1%} {name}')
