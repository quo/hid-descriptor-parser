#!/usr/bin/python3

import sys, os.path

itemnames = {
	#..0 = Main
	0x80: 'Input',
	0x90: 'Output',
	0xB0: 'Feature',
	0xA0: 'Collection',
	0xC0: 'End Collection',

	#..4 = Global
	0x04: 'Usage Page',
	0x14: 'Logical Minimum',
	0x24: 'Logical Maximum',
	0x34: 'Physical Minimum',
	0x44: 'Physical Maximum',
	0x54: 'Unit Exponent',
	0x64: 'Unit',
	0x74: 'Report Size',
	0x84: 'Report ID',
	0x94: 'Report Count',
	0xA4: 'Push',
	0xB4: 'Pop',

	#..8 = Local
	0x08: 'Usage',
	0x18: 'Usage Minimum',
	0x28: 'Usage Maximum',
}

collectionnames = [
	'Physical', 'Application', 'Logical', 'Report', 'Named Array', 'Usage Switch', 'Usage Modifier'
]

unitnames = {
	1: ['cm',   'g',    's', 'K', 'A', 'cd'],
	2: ['rad',  'g',    's', 'K', 'A', 'cd'],
	3: ['inch', 'slug', 's', 'F', 'A', 'cd'],
	4: ['deg',  'slug', 's', 'F', 'A', 'cd'],
}

class Collection:
	def __init__(self, name, usage):
		self.name = name
		self.usage = usage
		self.collections = []
		self.reports = []
	
	def has_reports(self):
		if self.reports: return True
		return any(c.has_reports() for c in self.collections)

class Report:
	def __init__(self, id, name):
		self.id = id
		self.name = name
		self.fields = []

class Field:
	def __init__(self, usage, count, flags, path, state):
		self.usage = usage
		self.count = count
		self.flags = flags
		self.path = path
		self.state = state

def parse(s):
	i = 0
	stack = []
	state = {}
	usages = []
	path = [Collection('Descriptor', None)]
	reports = {}
	useunit = False
	while i < len(s):
		b = s[i]
		i += 1
		l = [0,1,2,4][b & 3]
		nm = itemnames[b & ~3]
		val = 0
		for j in range(l):
			val |= s[i] << j*8
			i += 1
		# signed values
		if nm.startswith('Logical') or nm.startswith('Physical'):
			if l and val >> l*8-1: val -= 1 << l*8

		if nm == 'Push':
			stack.append(dict(state))
		elif nm == 'Pop':
			state = stack.pop()
		elif b & 0xc == 4: # global
			state[nm] = val
			if nm.startswith('Physical') or nm.startswith('Unit'): useunit = True
		elif nm == 'Collection':
			usage = usages[0] if usages else 0
			usages.clear()
			c = Collection(collectionnames[val], usage)
			path[-1].collections.append(c)
			path.append(c)
		elif nm == 'End Collection':
			path.pop()
		elif nm == 'Usage':
			if l <= 2: val |= state.get('Usage Page', 0) << 16
			usages.append(val)
		elif nm == 'Usage Minimum':
			if l <= 2: val |= state.get('Usage Page', 0) << 16
			usagemin = val
		elif nm == 'Usage Maximum':
			if l <= 2: val |= state.get('Usage Page', 0) << 16
			usages.extend(range(usagemin, val+1))
		elif nm in ('Feature', 'Input', 'Output'):
			# TODO use flags from val
			id = state.get('Report ID')
			try:
				r = reports[nm,id]
			except KeyError:
				reports[nm,id] = r = Report(id, nm)
			copy = dict(state)
			# XXX hack: according to spec, units should stay active until explicitly cleared, but a lot of descriptors never clear units
			if not useunit: copy['Unit'] = None
			n = state['Report Count']
			if n < len(usages): print('WARNING: Unused usages: ' + repr(usages[n:]))
			for j in range(n):
				if j >= len(usages)-1:
					f = Field(usages[j] if usages else 0, n-j, val, tuple(path), copy)
					r.fields.append(f)
					break
				f = Field(usages[j], 1, val, tuple(path), copy)
				r.fields.append(f)
			usages.clear()
			useunit = False
		else:
			raise Exception(nm)
	return reports

def build_tree(reports):
	for k,r in sorted(reports.items()):
		# find common base path for all fields
		path = None
		for f in r.fields:
			if path is None:
				path = f.path
			else:
				if len(f.path) < len(path):
					path = path[:len(f.path)]
				for i in range(len(path)):
					if path[i] is not f.path[i]:
						path = path[:i]
						break
		# put report in base collection
		path[-1].reports.append(r)
		# remove base from all paths
		for f in r.fields:
			f.path = f.path[len(path):]
	return path[0]


INDENT = '  '

usagenames = {}

def load_usages(fn):
	with open(fn) as f:
		for line in f:
			line = line.strip()
			if not line or line.startswith('#'): continue
			id, name = line.split('\t')
			if id.startswith('(') and id.endswith(')'):
				id = int(id[1:-1], 16)
				try: _, page = usagenames[id]
				except KeyError: page = {}
				usagenames[id] = name, page
			else:
				id = id.replace('\u2010', '-')
				if '-' in id: first, last = id.split('-')
				else: first = last = id
				first = int(first, 16)
				last = int(last, 16)
				for id in range(first, last+1): page[id] = name

def get_usage_label(usage):
	if not usage: return None
	page = usage >> 16
	usage = usage & 0xffff
	try:
		pgnm, pgusages = usagenames[page]
	except KeyError:
		pgnm = '?'
		pgusages = {}
	try:
		usgnm = pgusages[usage]
	except KeyError:
		usgnm = '?'
	return f'{page:02x}:{usage:02x} = {pgnm}: {usgnm}'

def print_collection(c, indent):
	if not c.has_reports(): return
	s = INDENT*indent
	print(s + c.name + ' ' + (get_usage_label(c.usage) or ''))
	for x in c.collections:
		print_collection(x, indent+1)
	for r in c.reports:
		print_report(r, indent+1)

def print_report(r, indent):
	s = INDENT*indent
	print(s + r.name + ('' if r.id is None else ' 0x%02x' % r.id))
	path = []
	for f in r.fields:
		while path and (len(path) > len(f.path) or path[-1] != f.path[len(path)-1]):
			path.pop()
		while len(path) < len(f.path):
			c = f.path[len(path)]
			path.append(c)
			print(INDENT*(indent+len(path)) + c.name + ' ' + (get_usage_label(c.usage) or ''))
		print_field(f, indent+len(path)+1)
	
def get_units(unit):
	try: names = unitnames[unit & 0xf]
	except KeyError: return hex(unit)
	ret = []
	for i in range(7):
		e = (unit >> 4+i*4) & 0xf
		if e > 7: e -= 16
		if e: ret.append((names[i], e))
	return ret

def print_field(r, indent):
	s = INDENT*indent
	sz = r.state.get('Report Size')
	tp = ('u' if r.state.get('Logical Minimum', 0) >= 0 else 'i') + str(sz)
	if r.count != 1: tp += '[%i]' % r.count

	logmin = r.state.get('Logical Minimum')
	logmax = r.state.get('Logical Maximum')
	unit = r.state.get('Unit')
	usagelabel = get_usage_label(r.usage)
	desc = s + tp + ' ' + (usagelabel or 'padding')
	if usagelabel and logmin != logmax:
		rangelabel = f'{logmin} to {logmax}' if logmin != 0 or logmax != (1<<sz)-1 else None
		physmin = r.state.get('Physical Minimum', 0)
		physmax = r.state.get('Physical Maximum')
		physlabel = None
		if unit and physmax is not None:
			exp = r.state.get('Unit Exponent', 0)
			if exp > 7: exp -= 16
			exp = 10**exp
			unitlabel = ' '.join(u if e == 1 else u+'^'+str(e) for u,e in get_units(unit))
			physlabel = f'{physmin*exp:.15g} to {physmax*exp:.15g} {unitlabel}'
		if rangelabel or physlabel:
			desc = '%-50s # ' % desc
			if rangelabel: desc += rangelabel
			if physlabel:
				if rangelabel: desc += ' = '
				desc += physlabel
	print(desc)

def main(filenames):
	for fn in ['hidusages.txt', 'hidusages-extra.txt']:
		load_usages(os.path.join(os.path.dirname(__file__), fn))
	for fn in filenames:
		print('File: ' + fn)
		with open(fn, 'rb') as f:
			data = f.read()
		if not data:
			print('Empty')
			continue
		desc = parse(data)
		#for k,r in sorted(desc.items()):
		#	print_report(r, 0)
		root = build_tree(desc)
		print_collection(root, 0)

if __name__ == '__main__':
	main(sys.argv[1:])

