import argparse
import math
from leo_ctrlplane import leo_ctrlplane_gen
# from plotters import export_subtrees_to_dot, export_original_tree_to_dot

def main():
	parser = argparse.ArgumentParser(
		description='This program generates control plane code for Leo.')
	
	grouped_args = parser.add_mutually_exclusive_group(required=True)
	grouped_args.add_argument('--sram', action='store_true', help='Use SRAM memory.')
	grouped_args.add_argument('--tcam', action='store_true', help='Use TCAM memory.')
	
	parser.add_argument('--output_filename', type=str, required=True, help='The output file name containing generated control plane code.')
	parser.add_argument('--sub_tree', type=int, required=True, help='Depth of sub-tree (2 = 3 nodes in a layer, 3 = 7 nodes in a layer, etc.)')
	parser.add_argument('--depth', type=int, required=True, help='The depth of the tree class (Excluding leaf layer).')
	parser.add_argument('--input_filename', type=str, required=True, help='The input tree from scikit-learn.')
	parser.add_argument('--transient', action='store_true', help='Enable support for transient state during runtime tree updates.')
	args = parser.parse_args()

	layers = 1 + int(math.ceil(args.depth / args.sub_tree))
	is_sram = args.sram

	code, feature_to_id = leo_ctrlplane_gen(args.input_filename, args.sub_tree, layers, is_sram, args.transient)

	# export_original_tree_to_dot(tree)
	# export_subtrees_to_dot(tree, layers_dict)

	with open(args.output_filename, 'w') as f:
		f.writelines(code)

	print('Exported control plane rules to:', args.output_filename)
	
	output_file = args.output_filename + "_feature_mappings.txt"
	with open(output_file, 'w') as f:
		for feat, i in feature_to_id.items():
			f.write("hdr.leo.feature_" + str(i) + " = " + feat + "\n")
	
	print("Exported feature mappings to:", output_file)

if __name__ == '__main__':
	main()
