import json
import mmh3
import re

with open('all_save_field_keys.json', 'r') as f:
    data = json.load(f)
typekeys = {k: [] for k in data['t']}
fieldkeys = {k: [] for k in data['f']}

basetypes = [s.encode('ascii') for s in (
    'u8', 'u16', 'u32', 'u64',
    's8', 's16', 's32', 's64',
    'f32', 'f64',
    'V2f', 'V3f',
    'V2i', 'V3i',
    'b', 'yml',
    'bool', 'C4f', 'C4u8', 'Str', 'WideStr', 'Bit', 'char', 'char16'
)]

def _attempt(keys, s):
    h = mmh3.hash(s)&0xFFFFFFFF
    if h in keys:
        s = s.decode('ascii')
        if s not in keys[h]:
            print('%10d/%x -> %r' % (h, h, s))
            keys[h].append(s)
        return True
    return False

def attempt(s):
    v = False
    v |= _attempt(fieldkeys, s)
    v |= _attempt(typekeys, s)
    v |= _attempt(typekeys, b'::' + s)
    v |= _attempt(typekeys, b'::Game::' + s)
    v |= _attempt(typekeys, b'::Game::Save' + s)
    return v

def attemptstr(s):
    return attempt(s.encode('ascii'))

for name in basetypes:
    _attempt(typekeys, name)

def buildWordgramPool():
    source_names = [s.strip() for s in open('allstr','rb')]
    pool = set()

    casesplitRE = re.compile(b'[A-Z][a-z]*')

    for name in source_names:
        # split this up into components
        bits = casesplitRE.findall(name)
        for groupSize in range(1, len(bits)):
            for i in range(len(bits) - groupSize + 1):
                group = bits[i:i+groupSize]
                pool.add(b''.join(group))

    print('Pool has %d strings' % len(pool))
    return pool

def buildStringPool():
    source_names = [s.strip() for s in open('allstr','rb')]
    return source_names

def strategy(pool):
    print('POOL SIZE', len(pool))
    maybe = set()
    for name in pool:
        if attempt(name):
            maybe.add(name)
    print('STAGE 1 DONE')
    for nameA in pool:
        for nameB in pool:
            if attempt(nameA + nameB):
                maybe.add(nameA)
                maybe.add(nameB)
    print('STAGE 2 DONE')
    print('%d maybes' % len(maybe))
    for a in maybe:
        for b in maybe:
            for c in maybe:
                attempt(a+b+c)

def allEnglishWords():
    def word_ok(word):
        if len(word) > 12:
            return False
        for c in word:
            if c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ':
                return False
        return True
    def casify(word):
        return word[0].upper() + word[1:].lower()
    words = [s.strip() for s in open('/usr/share/dict/words', 'r')]
    words = [casify(s).encode('ascii') for s in words if word_ok(s)]
    words.append(b'ID')
    words.append(b'Id')
    words.append(b'Id')
    words.append(b'Ftr')
    words.append(b'Npc')
    words.append(b'NSAID')
    words.append(b'POPID')
    words.append(b'Save')
    words.append(b'MyDesign')
    words.append(b'HalfUnit')
    words.append(b'ChangeStick')
    words.append(b'LandMaking')
    words.append(b'EventFlag')
    words.append(b'ItemName')
    for w in words[:]:
        words.append(w+b's')
    words = list(set(words))
    return words

def cxxFiltStrategy():
    # strings splatoon2_311_uncomp | grep "^_Z" | c++filt -n > splatoon_funcs
    symbols = [s.strip() for s in open('../splatoon_funcs', 'r')]
    pool = set()
    # n = 0
    print(len(symbols))
    for sym in symbols:
        if sym.startswith('guard variable'): continue
        if sym.startswith('vtable for'): continue
        if sym.startswith('non-virtual thunk'): continue
        if 'operator,' in sym or 'operator>' in sym: continue # bad news for my bad parser

        # yes, this is Bad
        # no, I don't care
        stack = []
        firstParen = None
        for i,c in enumerate(sym):
            if c == '(' and not stack:
                firstParen = i
            if c == '<' or c == '(':
                stack.append(i+1)
            elif c == ',':
                arg = sym[stack[-1]:i].strip()
                # print('arg:' + arg)
                pool.add(arg)
                pool.add(arg.replace(' const','').strip())
                pool.add(arg.replace('&','').replace('*','').replace(' const','').strip())
                stack[-1] = i+1
            elif c == '>' or c == ')':
                arg_start = stack.pop(-1)
                arg = sym[arg_start:i].strip()
                # print('arg:' + arg)
                pool.add(arg)
                pool.add(arg.replace(' const','').strip())
                pool.add(arg.replace('&','').replace('*','').replace(' const','').strip())

        if '::' in sym:
            if firstParen is None:
                pool.add(sym[:sym.rfind('::')])
            else:
                pool.add(sym[:sym.rfind('::', 0, firstParen)])

        # print(sym)
        # n += 1
        # if n > 20:
        #     break
    # print(pool)
    for p in pool:
        attempt(p.encode('ascii'))

def guessTypesStrategy():
    # this just... didn't help at all :v
    for prefix in ('', '::', 'sead::' ,'::sead::', '::Game::', '::Game::Save'):
        words = ('str','Str','string','String','word','Word')
        for w in words: attemptstr(prefix + w)
        for i in range(100):
            for w in words:
                attemptstr(f'{prefix}{w}{i}')
                attemptstr(f'{prefix}{w}<{i}>')
                attemptstr(f'{prefix}{w}[{i}]')

strategy(buildWordgramPool())
strategy(buildStringPool())
#strategy(allEnglishWords())
#cxxFiltStrategy()
#guessTypesStrategy()

with open('save_keys_manualCleanup4.json', 'w') as f:
    json.dump(dict(f=fieldkeys, t=typekeys), f, indent=4)
