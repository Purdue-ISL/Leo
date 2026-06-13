## Leo: Online ML-based Traffic Classification at Multi-Terabit Line Rate

Leo is an in-network traffic classification system that applies decision tree inference to every packet through a programmable switch. Leo supports a **class** of decision trees in a *run-time programmable* and *resource-efficient* manner while achieving multi-terabit line rate.

This artifact accompanies the paper: *"Leo: Online ML-based Traffic Classification at Multi-Terabit Line Rate"*. Syed Usman Jafri, Sanjay Rao, Vishal Shrivastav and Mohit Tawarmalani. In Proceedings of the 21th USENIX Symposium on Networked Systems Design and Implementation, NSDI '24, Santa Clara, CA, US.

If you use this artifact, please cite:
```
@inproceedings {leo_nsdi_2024,
author = {Syed Usman Jafri and Sanjay Rao and Vishal Shrivastav and Mohit Tawarmalani},
title = {Leo: Online {ML-based} Traffic Classification at {Multi-Terabit} Line Rate},
booktitle = {21st USENIX Symposium on Networked Systems Design and Implementation (NSDI 24)},
year = {2024},
isbn = {978-1-939133-39-7},
address = {Santa Clara, CA},
pages = {1573--1591},
url = {https://www.usenix.org/conference/nsdi24/presentation/jafri},
publisher = {USENIX Association},
month = apr
}
```
## 1. Pre-requisites:

### 1A. Hardware:

- Intel® Tofino™ Switch
- Server (equipped with NIC)

We use the **EdgeCore Wedge-100BF-32x** switch for our evaluation.

### 1B. Software:

- Intel Barefoot SDK 9.11.1
- Ubuntu 22.04
- Python 3.10.12
- scikit-learn 1.3.0
- Scapy 2.5
- pandas 2.0.3
- GNU Make 4.3
- matplotlib 3.7.2

While using Ubuntu 22.04 as the operating system is not a hard requirement, it is what was used for all our evaluation.

## 2. Datasets

The following two datasets for evaluating classifation accuracy of Leo and related work.

- [UNSW-NB15](https://research.unsw.edu.au/projects/unsw-nb15-dataset)
- [CICIDS-2017](https://www.unb.ca/cic/datasets/ids-2017.html)

These datasets should be downloaded separately and placed in the `dataset-simulation` directory in the following hierarchy:

```
Leo/
 |_ dataset-simulation/
    |_ UNSW-NB15/
       |_ Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv
       |_ Friday-WorkingHours-Morning.pcap_ISCX.csv
       |_ ...
    |_ CICIDS-2017/
       |_ UNSW-NB15_1.csv
       |_ UNSW-NB15_2.csv
       |_ ...
  |_ ...
```

## 3. Leo parameters

Leo generates a hardware mapping based on a set of parameters that identify a decision tree. The following parameters are available to the user:

**SUB_TREE_SIZE** - The degree of flattening Leo applies at every layer. For example, `SUB_TREE_SIZE=2` flattens 2 levels (3 nodes) of the tree to the same layer. `SUB_TREE_SIZE=3` flattens 3 levels (7 nodes) and so on.

**MEM_TYPE** - The type of memory to use for the boolean tables. Possible options: `SRAM` or `TCAM`.

**DEPTH** - The maximum number of internal layers to implement. For example, `DEPTH=7` will produce 7 layers of internal nodes plus an additional layer of leaf nodes.

**LEAVES** - A limit on the number of leaves on each level of the tree. Note: `LEAVES=0` will allow the tree to grow naturally with no leaf limit.

**FEATURES** - The number of features the the tree should support.

## 4. Using Leo

### 4A. Setting up the data plane

The following steps outline how to deploy Leo on real switch.

1. Identify the target Leo tree class you would like to support. The available parameters are explained in Section 3.

2. Clone the Leo repository on your switch.

    ```
    git clone git@github.com:Purdue-ISL/Leo.git
    ```

3. Open a console and navigate to Leo P4 generator sub-folder of the Leo repository.

    ```
    cd Leo/leo-generator
    ```

4. Run the Leo P4 generator, which is used as follows:

    ```
    python3 leo_dataplane_generator.py [-h] (--sram | --tcam) --filename <output P4 file name>
    --sub_tree SUB_TREE_SIZE --depth DEPTH --features FEATURES
    [--leaf_limit LEAVES] [--transient]
    ```

    For example, for a tree class using SRAM memory with maximum depth 10, 12 features and a sub-tree size of 2 invoke the following command:

    ```
    python3 leo_dataplane_generator.py --sram --filename demo.p4 --sub_tree 2 --depth 10
    --features 12
    ```

    To introduce a leaf limit of 500 leaves add the `--leaf_limit` flag as follows:

    ```
    python3 leo_dataplane_generator.py --sram --filename demo.p4 --sub_tree 2 --depth 10
    --features 12 --leaf_limit 500
    ```

    To enable support for handling transient states during runtime tree updates add the `--transient` flag.

5. Create a `build` folder. This folder will contain the compiled binary and other supporting files to run the switch.

    ```
    mkdir build
    ```

6. Setup the build directory. Make sure the `$SDE` and `$SDE_INSTALL` environment variables were setup during the Barefoot SDK installation.

    ```
    cmake $SDE/p4studio -DCMAKE_INSTALL_PREFIX=$SDE_INSTALL -DCMAKE_MODULE_PATH=$SDE/cmake
    -DTOFINO=ON -DTOFINO2=OFF -DP4_LANG=p4_16 -DP4_NAME=Leo -DP4_PATH=$HOME/Leo/leo-generator/demo.p4
    ```

7. Invoke the Tofino compiler to generate the switch binary:

    ```
    sudo make
    sudo make install
    ```

8. Finally, deploy the switch binary to the switch:

    ```
    sudo -E $SDE/run_switchd.sh -p Leo
    ```

### 4B. Setting up the control plane

1. Once the switch is up and running with Leo, enable the switch ports for trasmission. In this example, the ports `33/0` and `33/2` are enabled to allow forwarding packets to the switch CPU. The ports `2/-` and `4/-` are connected to the server.

    **Note:** the port numbers may vary based on how the cables between the switch and server were connected.

    ```
    ucli
    port-add 33/0 10G NONE
    port-add 33/2 10G NONE
    port-add 2/- 100G NONE
    port-add 4/- 100G NONE
    port-enb 33/0
    port-enb 33/2
    port-enb 2/0
    port-enb 4/0
    exit
    ```

2. Open a console and navigate to Leo P4 generator sub-folder of the Leo repository.

    ```
    cd Leo/leo-generator
    ```

3. Train the decision tree model using Python3's scikit-learn library. Make sure the `DEPTH` and `LEAVES` parameter are configured during training.

    - Please see the scikit-learn [documentation](https://scikit-learn.org/0.21/documentation.html) for usage instructions.
    
    - For the two datasets used for in our evaluation, we provide sample training scripts in the *dataset-simulation* folder.

    - In addition to the depth and leaves parameters, ensure that the number of features is set to `FEATURES`. We provide a function `select_features(...)` in the sample training scripts for this purpose. The function runs the Recursive Feature Elimination algorithm to identify the best subset of features for training.

    - Once the model is trained, use scikit-learn's `export_text(...)` function to export the trained model to a text file.

4. Invoke the Leo generator to generate control plane code.

    **Note:** Make sure that the `SUB_TREE_SIZE` and `DEPTH` parameters match those used earlier for generating the data plane in *Section 4a (4)*.

    ```
    python3 leo_ctrlplane_generator.py [-h] (--sram | --tcam) --output_filename <output P4 filename>
    --sub_tree SUB_TREE_SIZE --depth DEPTH --input_filename <output tree from scikit-learn> [--transient]
    ```

5. Switch into the Python Barefoot control plane and execute the generated Leo control plane code.

    Copy the the control plane code from the previous step (`--output_filename`) into the following block of code:

    ```
    bfrt_python
    cmds='''<GENERATED LEO CONTROL PLANE HERE>'''
    exec(cmds)
    ```

**Note on feature extraction:**

The Leo generator also produces a text file *feature_mapping.txt* that lists which Leo feature header should be populated with which feature from the dataset.

**Example feature mapping for CICIDS-2017:**
```
hdr.leo.feature_1 = SYNFlagCount
hdr.leo.feature_2 = MinPacketLength
hdr.leo.feature_3 = DestinationPort
...
```

The user will have to provide P4 code to extract features from the packet (or stateful features from registers). This is not done automatically, since feature extraction logic is dependant on the type of feature itself.

Look for the following markers in the generated P4 code:

- `// Declare stateful features registers here`
- `// Execute stateful features registers here`
- `// Populate features to hdr.leo.feature_i here`

To see an example what feature extraction code may look like, please see *Leo/leo-1m-flows.p4*. This is a TCAM implementation that supports 1 million flows using 4 stateful and 1 stateless feature in a TCAM-based 10-depth tree.

## 5. Using the resource models

### 5A. Leo

The Leo resource model calculates the number of table entries required for a target decision tree class. The model implements the analysis presented in Section 6 of the paper.

**Usage:**

```
python3 resource-model.py [-h] (--sram | --tcam) [--transient]
--muxed_alu_config MUXED_ALU_CONFIG
```

- `MUXED_ALU_CONFIG` represents a comma-separated list of the number of Muxed ALUs in a switch stage. For example, `7,3,3,1` means: 7 Muxed ALUs (3 tree levels) in the first stage, 3 Muxed ALUs (2 tree levels) in the second and third stages and 1 Muxed ALU (1 tree level) in the fourth stage.
- Only one of `--sram` or `--tcam` can be supplied. This controls whether to calculate memory requirements for Leo-SRAM or Leo-TCAM.
- Include the `--transient` argument to include the additional overhead when accounting for transient state handling for runtime tree updates.

Note that an additional layer for the leaf layer is added automatically.

### 5B. IIsy

The IIsy resource model calculates the total number of table entries required and implements the analysis presented in Section 3 - Propositions 1 and 2, Appendix A.1 and A.2 of the paper.

**Usage - Proposition 1 (SRAM):**

```
python3 resource-model.py p1 [-h] --n N --d D --k K
```
- `N` is the number of features
- `D` is the depth of the tree (excluding leaf layer).
- `K` is the maximum feature value.

**Usage - Proposition 2 (TCAM):**

```
python3 resource-model.py p2 [-h] --filename FILENAME --N_max N_MAX --K_power_max K_POWER_MAX
```

With the `p2` argument, the resource model produces a CSV file containing the resource required for the proposition 2 family of trees using a variety of `N`, `K` combinations.

- `N_MAX` is the maximum number of features to explore up to. For example, `--N_max 5` will explore N=2, 3, 4, 5.
- `K_POWER_MAX` is the maximum feature value K to explore up to. Represented as a power of 2. For example, `--K_power_max 4` will explore K=3, 7, 15.

**Usage - TCAM feature table:**

```
python3 worst-case-feature-table.py [-h] --width WIDTH --upper_lim UPPER_LIM --leaves LEAVES
```

- `WIDTH` is the width of the features (in number of bits).
- `UPPER_LIM` is the maximum value a feature can take.
- `LEAVES` is the number of leaf nodes in the tree class.

## 6. License

The P4 code in this repository makes use of Tofino externs/includes which can be openly published under [Open-Tofino](https://github.com/barefootnetworks/Open-Tofino). ~~Note that you will still need to obtain a license to use the Intel Barefoot SDK to compile the P4 code.~~

**UPDATE:** As of 6/12/2026, Intel has open-sourced the SDK [here](https://github.com/p4lang/open-p4studio)!
   
## 7. Contact
Please contact ```jafri3@purdue.edu``` for any questions.