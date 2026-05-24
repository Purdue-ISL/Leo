from string import Template

stateless_AND_alu_T = Template('''
	action ALU_${alu}_and() {
		hdr.leo.alu_${alu}_result = hdr.leo.alu_${alu}_input & 32768;
	}
''')

mux_action_decl_with_result_t = Template('''
	action set_${layer}_${alu}_feature${feature}(bit<LEAF_ID_WIDTH> result, bit<FEATURE_WIDTH> constraint) {
		hdr.leo.layer_${layer_prev}_result = result;
		hdr.leo.alu_${alu}_input = hdr.leo.feature_${feature} + constraint;
	}
''')

mux_action_alt_decl_with_result_t = Template('''
	action set_${layer}_${alu}_feature${feature}(bit<LEAF_ID_WIDTH> result, bit<FEATURE_WIDTH> constraint) {
		hdr.leo.layer_${layer_prev}_result = result;
		hdr.leo.alu_${alu}_input_B = hdr.leo.feature_${feature} + constraint;
	}
''')

mux_action_decl_t = Template('''
	action set_${layer}_${alu}_feature${feature}(bit<FEATURE_WIDTH> constraint) {
		hdr.leo.alu_${alu}_input = hdr.leo.feature_${feature} + constraint;
	}
''')

mux_action_alt_decl_t = Template('''
	action set_${layer}_${alu}_feature${feature}(bit<FEATURE_WIDTH> constraint) {
		hdr.leo.alu_${alu}_input_B = hdr.leo.feature_${feature} + constraint;
	}
''')

mux_table_t = Template('''
	table layer_${layer}_${alu} {
		key = {${keys}
		}
		actions = {${actions}
			NoAction;
		}
		size = ${table_size};
		default_action = NoAction();
	}
''')

mux_action_t = Template('''
			set_${layer}_${alu}_feature${feature};''')

mux_key_t = Template('''
			hdr.leo.${key_name} : ${table_type};''')

custom_header_t = Template('''
#define FEATURE_WIDTH 16
#define LEAF_ID_WIDTH 16

header leo_hdr_t {
	bit<LEAF_ID_WIDTH> leaf;
	bit<1> tree_id;
	bit<7> padding;
${hdrs}\tbit<48> start_time;
	bit<48> end_time;
	bit<48> backup_time;
}
''')

apply_t = Template('''
	apply {
${layer_apply}
		hdr.leo.end_time = eg_intr_from_prsr.global_tstamp;
	}
}
''')


egress_parser_deparser = '''
// ---------------------------------------------------------------------------
// Egress Parser
// ---------------------------------------------------------------------------
parser SwitchEgressParser(
		packet_in pkt,
		out header_t hdr,
		out metadata_t eg_md,
		out egress_intrinsic_metadata_t eg_intr_md) {

	state start {
		pkt.extract(eg_intr_md);
		transition parse_ethernet;
	}

	state parse_ethernet {
		pkt.extract(hdr.ethernet);
		transition select(hdr.ethernet.ether_type) {
			ETHERTYPE_IPV4 : parse_ipv4;
			default : reject;
		}
	}

	state parse_ipv4 {
		pkt.extract(hdr.ipv4);
		transition select(hdr.ipv4.protocol){
			IP_PROTOCOLS_TCP: parse_tcp;
			default: reject;
		}
	}

	state parse_tcp {
	   pkt.extract(hdr.tcp);
	   transition parse_class_hdr;
	}

	state parse_class_hdr {
	   pkt.extract(hdr.leo);
	   transition accept;
	}
}

// ---------------------------------------------------------------------------
// Egress Deparser
// ---------------------------------------------------------------------------
control SwitchEgressDeparser(packet_out pkt,
							  inout header_t hdr,
							  in metadata_t eg_md,
							  in egress_intrinsic_metadata_for_deparser_t 
								eg_intr_dprsr_md
							  ) {

	apply {
		pkt.emit(hdr.ethernet);
		pkt.emit(hdr.ipv4);
		pkt.emit(hdr.tcp);
		pkt.emit(hdr.leo);
	}
}

// ---------------------------------------------------------------------------
// Egress 
// ---------------------------------------------------------------------------
control SwitchEgress(
		inout header_t hdr,
		inout metadata_t eg_md,
		in egress_intrinsic_metadata_t eg_intr_md,
		in egress_intrinsic_metadata_from_parser_t eg_intr_from_prsr,
		inout egress_intrinsic_metadata_for_deparser_t eg_intr_md_for_dprsr,
		inout egress_intrinsic_metadata_for_output_port_t eg_intr_md_for_oport) {
        
	action set_leaf(bit<LEAF_ID_WIDTH> leaf) {
		hdr.leo.leaf = leaf;
	}
'''


footer = '''
Pipeline(SwitchIngressParser(),
		 SwitchIngress(),
		 SwitchIngressDeparser(),
		 SwitchEgressParser(),
		 SwitchEgress(),
		 SwitchEgressDeparser()) pipe;

Switch(pipe) main;
'''

std_headers = '''
#include <core.p4>
#if __TARGET_TOFINO__ == 3
#include <t3na.p4>
#elif __TARGET_TOFINO__ == 2
#include <t2na.p4>
#else
#include <tna.p4>
#endif

const bit<16> ETHERTYPE_IPV4 = 16w0x0800;
const bit<8> IP_PROTOCOLS_TCP = 6;

header ethernet_h {
	bit<48> dst_addr;
	bit<48> src_addr;
	bit<16> ether_type;
}

header ipv4_h {
	bit<4> version;
	bit<4> ihl;
	bit<8> diffserv;
	bit<16> total_len;
	bit<16> identification;
	bit<3> flags;
	bit<13> frag_offset;
	bit<8> ttl;
	bit<8> protocol;
	bit<16> hdr_checksum;
	bit<32> src_addr;
	bit<32> dst_addr;
}

header tcp_h {
	bit<16> src_port;
	bit<16> dst_port;
	bit<32> seq_no;
	bit<32> ack_no;
	bit<4> data_offset;
	bit<4> res;
	bit<1>  cwr;
	bit<1>  ece;
	bit<1>  urg;
	bit<1>  ack;
	bit<1>  psh;
	bit<1>  rst;
	bit<1>  syn;
	bit<1>  fin;
	bit<16> window;
	bit<16> checksum;
	bit<16> urgent_ptr;
}
'''

ingress_parser_deparser = '''
header resubmit_header_t {
	bit<8>  type;
	bit<8> class_id;
	}

struct header_t {
	ethernet_h ethernet;
	ipv4_h ipv4;
	tcp_h tcp;
	leo_hdr_t leo;
}

const bit<8> RESUB_TYPE = 255;

struct metadata_t {
	bit<8>          resub_type;
	resubmit_header_t resub_hdr;
}

typedef bit<9>  egressSpec_t;

// ---------------------------------------------------------------------------
// Ingress parser
// ---------------------------------------------------------------------------
parser SwitchIngressParser(
		packet_in pkt,
		out header_t hdr,
		out metadata_t ig_md,
		out ingress_intrinsic_metadata_t ig_intr_md) {

	state start {
	   pkt.extract(ig_intr_md);
	   ig_md.resub_type = 0;
		transition select(ig_intr_md.resubmit_flag) {
			1 : parse_resubmit;
			0 : parse_port_metadata;
		}
	}

	state parse_resubmit {
		ig_md.resub_type = pkt.lookahead<bit<8>>()[7:0];
		transition select(ig_md.resub_type) {
			RESUB_TYPE : parse_resub;
			default : reject;
		}
	}

	state parse_resub {
		pkt.extract(ig_md.resub_hdr);
		transition parse_resub_end;
	}

	state parse_resub_end {
		transition parse_ethernet;
	}

	state parse_port_metadata {
		pkt.advance(PORT_METADATA_SIZE);
		transition parse_ethernet;
	}

	state parse_ethernet {
		pkt.extract(hdr.ethernet);
		transition select(hdr.ethernet.ether_type) {
			ETHERTYPE_IPV4: parse_ipv4;
			default: reject;
		}
	}

	state parse_ipv4 {
		pkt.extract(hdr.ipv4);
		transition select(hdr.ipv4.protocol){
			IP_PROTOCOLS_TCP: parse_tcp;
			default: reject;
		}
	}

	state parse_tcp {
	   pkt.extract(hdr.tcp);
	   transition parse_class_hdr;
	}

	state parse_class_hdr {
	   pkt.extract(hdr.leo);
	   transition accept;
	}
}

// ---------------------------------------------------------------------------
// Ingress Deparser
// ---------------------------------------------------------------------------
control SwitchIngressDeparser(
		packet_out pkt,
		inout header_t hdr,
		in metadata_t ig_md,
		in ingress_intrinsic_metadata_for_deparser_t ig_dprsr_md) {

	Checksum() ipv4_checksum;

	apply {
		hdr.ipv4.hdr_checksum = ipv4_checksum.update({
			hdr.ipv4.version,
			hdr.ipv4.ihl,
			hdr.ipv4.diffserv,
			hdr.ipv4.total_len,
			hdr.ipv4.identification,
			hdr.ipv4.flags,
			hdr.ipv4.frag_offset,
			hdr.ipv4.ttl,
			hdr.ipv4.protocol,
			hdr.ipv4.src_addr,
			hdr.ipv4.dst_addr});

		pkt.emit(hdr.ethernet);
		pkt.emit(hdr.ipv4);
		pkt.emit(hdr.tcp);
		pkt.emit(hdr.leo);
	}
}

// ---------------------------------------------------------------------------
// Ingress 
// ---------------------------------------------------------------------------
control SwitchIngress(
		inout header_t hdr,
		inout metadata_t ig_md,
		in ingress_intrinsic_metadata_t ig_intr_md,
		in ingress_intrinsic_metadata_from_parser_t ig_prsr_md,
		inout ingress_intrinsic_metadata_for_deparser_t ig_dprsr_md,
		inout ingress_intrinsic_metadata_for_tm_t ig_tm_md) {

	const PortId_t CPU_PORT = 64;

	action drop() {
		ig_dprsr_md.drop_ctl = 1;
	}

	action ipv4_forward(egressSpec_t port) {
		ig_tm_md.ucast_egress_port = port;
		hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
	}

	action send_to_cpu() {
		ig_tm_md.ucast_egress_port = CPU_PORT;
	}

	table ipv4_exact {
		key = {
			hdr.ipv4.dst_addr: exact;
		}
		actions = {
			ipv4_forward;
			send_to_cpu;
			drop;
		}
		size = 10000;
		default_action = send_to_cpu();
	}
    
	action change_active_tree(bit<1> tree_id) {
		hdr.leo.tree_id = tree_id;
	}
    
	action default_tree() {
		hdr.leo.tree_id = 0;
	}
    
	table tree_id_table {
		key = {
			hdr.ipv4.src_addr: ternary;
		}
		actions = {
			change_active_tree;
            default_tree;
		}
		size = 1;
		default_action = default_tree();
	}
    
    // Declare stateful features registers here
    
	apply {
		hdr.leo.start_time = ig_intr_md.ingress_mac_tstamp;
        tree_id_table.apply();
        
        // Execute stateful features registers here
        // Populate features to hdr.leo.feature_i here

		if (hdr.ipv4.isValid()) {
			ipv4_exact.apply();
		}
	}
}
'''

add_leaf_node_entry_t = Template('''bfrt.Leo.pipe.SwitchEgress.layer_${layer}_1.add_with_set_leaf(${key_str}, leaf=${leaf_class})''')

add_internal_node_entry_t = Template('''bfrt.Leo.pipe.SwitchEgress.layer_${layer}_${alu}.add_with_set_${layer}_${alu}_feature${feature_id}(${args})''')

clear_table_entry_t = Template('''bfrt.Leo.pipe.SwitchEgress.layer_${layer_id}_${alu}.clear()''')

dump_table_entry_t = Template('''bfrt.Leo.pipe.SwitchEgress.layer_${layer_id}_${alu}.dump(table=1)''')