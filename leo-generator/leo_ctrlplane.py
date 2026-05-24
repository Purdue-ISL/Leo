import importlib 
import sys
import os
import itertools
from leo_templates import *

class InternalNode:
	def __init__(self, feature, constraint, depth):
		self.feature = feature
		self.constraint = constraint
		self.depth = depth
		self.left = None
		self.right = None

class LeafNode:
	def __init__(self, label, depth):
		self.label = label
		self.depth = depth

class Tree:
	def __init__(self, node):
		self.root = node

	def print_tree(self, node, level, prefix='ROOT'):
		if node is not None:
			if type(node) == InternalNode:
				print('|   ' * level + prefix, node.feature, node.constraint)
				if node.left is not None or node.right is not None:
					self.print_tree(node.left, level + 1, 'L   ')
					self.print_tree(node.right, level + 1, 'R   ')
			else:
				print('|   ' * level + prefix, node.label)

def parse_line(line):
	line = line.replace('|---', '|   ')
	depth = line.count('|   ')
	leaf = 'class' in line
	line = line.strip('|   ')
	line = line.split(' ')
	if leaf:
		label = int(line[1])
		return (leaf, depth, label)
	else:
		feature = line[0]
		condition = line[1]
		constraint = int(round(float(line[-1])))
		return (leaf, depth, feature, condition, constraint)

def find_my_right(node_lines, line_num, depth):
	for i in range(line_num, len(node_lines)):
		if node_lines[i][1] == depth:
			return i

	return None

def build_tree_recursive(node_lines, node, line_num):
	if line_num >= len(node_lines):
		return None

	tup = node_lines[line_num]
	if tup[0]:
		return None
	else:
		right_subtree_line_num = 1 + find_my_right(node_lines, line_num + 1, tup[1])
		right_node = node_lines[right_subtree_line_num]
		left_node = node_lines[line_num + 1]
		
		if left_node[0]:
			node.left = LeafNode(left_node[2], left_node[1])
		else:
			node.left = InternalNode(left_node[2], left_node[4], left_node[1])
			build_tree_recursive(node_lines, node.left, line_num + 1)

		if right_node[0]:
			node.right = LeafNode(right_node[2], right_node[1])
		else:
			node.right = InternalNode(right_node[2], right_node[4], right_node[1])
			build_tree_recursive(node_lines, node.right, right_subtree_line_num)
		
		return node

def build_tree_from_file(file):
	f = open(file, 'r')
	lines = f.readlines()
	f.close()

	nodes = []
	for line in lines:
		nodes.append(parse_line(line))

	root = InternalNode(nodes[0][2], nodes[0][4], nodes[0][1])
	build_tree_recursive(nodes, root, 0)
	tree = Tree(root)
	return tree

def find_k_children(node, k):
	children = []
	queue = [node]
	while len(queue) > 0:
		cur_node = queue.pop(0)
		children.append(cur_node)
		if len(children) == k:
			break

		if type(cur_node.left) == InternalNode:
			queue.append(cur_node.left)

		if type(cur_node.right) == InternalNode:
			queue.append(cur_node.right)

	return children

def sub_tree_splitter(root, K):
	layers = {}
	queue = [(root, 1)] # (node, layer_id)

	while len(queue) > 0:
		node, layer_id = queue.pop(0)
		if type(node) == list:
			if layer_id not in layers:
				layers[layer_id] = []
			
			layers[layer_id].append(node)
			continue
			
		children = find_k_children(node, K)

		if layer_id not in layers:
			layers[layer_id] = []
		
		layers[layer_id].append(children)

		leaf_nodes = []
		for c in children:
			if type(c.left) == InternalNode and c.left not in children:
				queue.append((c.left, layer_id + 1))
			elif type(c.left) == LeafNode:
				leaf_nodes.append(c.left)
				
			if type(c.right) == InternalNode and c.right not in children:
				queue.append((c.right, layer_id + 1))
			elif type(c.right) == LeafNode:
				leaf_nodes.append(c.right)
				
		for leaf in leaf_nodes:
			queue.append(([leaf], layer_id + 1))

	return layers

def assign_rule_to_layers(layers, subtree_layer_limits):
	assigned_layers = []
	for l in range(1, len(subtree_layer_limits) + 1):
		layer_limit = subtree_layer_limits[l - 1]
		curr_group = []
		sub_groups = layers[l]
		if len(sub_groups) > layer_limit:
			print('ERROR:', len(sub_groups), "ALUs needed. Limit:", layer_limit)
		
		for rule in sub_groups[:layer_limit]:
			curr_group.append(rule)

		assigned_layers.append((l, curr_group))

	return assigned_layers

def build_parent_map(node, parent_map):
	if parent_map is None:
		parent_map = {}
	
	if type(node) == InternalNode:
		if node.left is not None:
			parent_map[id(node.left)] = (node, 1) # 1 = left/true
			build_parent_map(node.left, parent_map)
		if node.right is not None:
			parent_map[id(node.right)] = (node, 0) # 0 = right/false
			build_parent_map(node.right, parent_map)
	
	return parent_map

def generate_combinations(fixed, K):
	selected_combos = []
	all_combos = itertools.product([0, 1], repeat=K)
	for curr_combo in all_combos:
		valid = True
		for i, value in fixed.items():
			if curr_combo[i] != value:
				valid = False
				break
		
		if valid:
			selected_combos.append(curr_combo)
	
	return selected_combos

def generate_clear_tables(layers, k):
	code = []
	for i, layer in enumerate(layers):
		if i == len(layers) - 1:
			max_alu = 1
		else:
			max_alu = k
		
		for alu in range(1, max_alu + 1):
			clear_table = clear_table_entry_t.substitute(layer_id=layer[0], alu=alu)
			code.append(clear_table)
	
	return code

def generate_dump_tables(layers, k):
	code = []
	for i, layer in enumerate(layers):
		if i == len(layers) - 1:
			max_alu = 1
		else:
			max_alu = k
		
		for alu in range(1, max_alu + 1):
			dump_table = dump_table_entry_t.substitute(layer_id=layer[0], alu=alu)
			code.append(dump_table)
	
	return code

def get_unique_features(node, features):
	if features is None:
		features = []
	
	if type(node) == InternalNode:
		if node.feature not in features:
			features.append(node.feature)
		
		get_unique_features(node.left, features)
		get_unique_features(node.right, features)
	
	return features

def export_feature_mappings(tree):
	features = get_unique_features(tree.root, None)
	feature_to_id = {}
	i = 1
	for f in features:
		feature_to_id[f] = i
		i += 1
	
	# output_file = 'feature_mapping.txt'
	# with open(output_file, 'w') as f:
	# 	for feat, i in feature_to_id.items():
	# 		f.write("hdr.leo.feature_" + str(i) + " = " + feat + "\n")
	
	# print("Exported feature mappings to:", output_file)
	return feature_to_id

def assign_subtree_ids(layers):
	node_to_subtree = {}
	node_to_subtreeid = {}
	
	subtree_counter = 0
	for layer, subtrees in layers:
		for subtree in subtrees:
			if type(subtree[0]) == InternalNode:
				node_to_subtreeid[id(subtree)] = subtree_counter
				subtree_counter += 1
			
			for node in subtree:
				node_to_subtree[id(node)] = subtree
	
	return node_to_subtree, node_to_subtreeid

def get_parent_subtree_constraints(target_node, parent_map, node_to_subtree, node_to_subtreeid):
	if id(target_node) not in parent_map:
		return None, {}
	
	parent_node, is_left = parent_map[id(target_node)]
	parent_subtree = node_to_subtree[id(parent_node)]
	parent_subtreeid = node_to_subtreeid[id(parent_subtree)]
	
	constraints = {}
	curr = target_node
	while curr != parent_subtree[0]:
		p, is_left = parent_map[id(curr)]
		i = parent_subtree.index(p)
		constraints[i] = is_left
		curr = p
	
	return parent_subtreeid, constraints

def generate_func_inputs(combos, layer, parent_id):
	inputs = []
	for combo in combos:
		pos_args = []
		if layer == 1:
			pos_args.append('0')
		else:
			if layer > 2:
				pos_args.append(str(parent_id))
			
			for value in combo:
				if value == 1:
					hw_val = 32768
				else:
					hw_val = 0
				
				pos_args.append(str(hw_val))
				
		inputs.append(', '.join(pos_args))
	
	return inputs

def generate_func_inputs_tcam(fixed, layer, parent_id, k):
	pos_args = []
	if layer == 1:
		pos_args.extend(['0', '1'])
	else:
		if layer > 2:
			pos_args.extend([str(parent_id), '0xffff'])
		
		for a in range(k):
			if a in fixed:
				if fixed[a] == 1:
					hw_val = 32768
				else:
					hw_val = 0
				
				hw_mask = 32768
			else:
				hw_val = 0
				hw_mask = 0
			
			pos_args.extend([str(hw_val), str(hw_mask)])
			
	code = [', '.join(pos_args)]
	return code


def generate_rule_commands(layer, subtree, target_node, key_strs, k, feature_to_id, subtree_str_id, is_leaf):
	code = []
	if is_leaf:
		leaf_class = target_node.label
		for key_str in key_strs:
			rule = add_leaf_node_entry_t.substitute(layer=layer, key_str=key_str, leaf_class=leaf_class)
			code.append(rule)
	else:
		for a in range(1, k + 1):
			for key_str in key_strs:
				if a <= len(subtree):
					n = subtree[a - 1]
					feat_id = feature_to_id[n.feature]
					constraint_val = (-n.constraint) & 0xFFFF
					if key_str:
						args = [key_str]
					else:
						args = []
					
					if a == 1 and layer > 1:
						args.append("result=" + str(subtree_str_id))
					
					args.append("constraint=" + str(constraint_val))
					arg_str = ", ".join(args)
					rule = add_internal_node_entry_t.substitute(layer=layer, alu=a, feature_id=feat_id, args=arg_str)
					code.append(rule)
	
	return code

def generate_subtree_rules(layers, parent_map, node_to_subtree, node_to_subtreeid, feature_to_id, k, is_sram):
	code = []
	for layer, subtrees in layers:
		for subtree in subtrees:
			is_leaf = False
			if type(subtree[0]) == LeafNode:
				is_leaf = True
				nodes_to_process = subtree
			else:
				nodes_to_process = [subtree[0]]
			
			for target_node in nodes_to_process:
				parent_id, fixed = get_parent_subtree_constraints(target_node, parent_map, node_to_subtree, node_to_subtreeid)
				
				if is_sram:
					combos = generate_combinations(fixed, k)
					if layer == 1:
						combos = [()]
					
					func_inputs = generate_func_inputs(combos, layer, parent_id)
				else:
					func_inputs = generate_func_inputs_tcam(fixed, layer, parent_id, k)
				
				subtree_id_temp = id(subtree)
				if subtree_id_temp in node_to_subtreeid:
					subtree_id = node_to_subtreeid[subtree_id_temp]
				else:
					subtree_id = 'LEAF'
				
				func_calls = generate_rule_commands(layer, subtree, target_node, func_inputs, k, feature_to_id, subtree_id, is_leaf)
				
				code.append("# Subtree with ID: " + str(subtree_id) + " | HW Layer: " + str(layer))
				code.extend(func_calls)
	
	return code

def leo_ctrlplane_gen(filename, sub_tree, num_layers, is_sram, transient):
	if transient:
		print('Disabled transient control plane support for now...')

	sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
	leo_resource_model = importlib.import_module('leo.resource-model')

	num_alus = (2 ** sub_tree) - 1
	alu_config = [num_alus] * num_layers
	subtree_layer_limits = leo_resource_model.leo_model(alu_config, is_sram, transient)
	subtree_layer_limits = subtree_layer_limits[:-1]

	tree = build_tree_from_file(filename)
	sub_groups = sub_tree_splitter(tree.root, num_alus)
	layers = assign_rule_to_layers(sub_groups, subtree_layer_limits)

	code = []
	code.extend(generate_clear_tables(layers, num_alus))
	
	parent_map = build_parent_map(tree.root, None)
	feature_to_id = export_feature_mappings(tree)
	node_to_subtree, node_to_subtreeid = assign_subtree_ids(layers)
	
	full_tree_rules = generate_subtree_rules(layers, parent_map, node_to_subtree, node_to_subtreeid, feature_to_id, num_alus, is_sram)
	code.extend(full_tree_rules)
	code.extend(generate_dump_tables(layers, num_alus))

	add_newlines = []
	for line in code:
		add_newlines.append(line + '\n')
	
	return add_newlines, feature_to_id
