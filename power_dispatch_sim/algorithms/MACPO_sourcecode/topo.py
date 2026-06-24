import numpy as np

def generate_chain_topology(n_nodes):
    # 初始化 n_nodes x n_nodes 的零矩阵
    adjacency_matrix = np.eye((n_nodes))
    
    # 填充链式拓扑的邻接关系
    for i in range(n_nodes - 1):
        adjacency_matrix[i][i + 1] = 1
        adjacency_matrix[i + 1][i] = 1
    row_sums = adjacency_matrix.sum(axis=1, keepdims=True)
    normalized_matrix = adjacency_matrix / row_sums
    return normalized_matrix

# 设置节点数
n_nodes = 20
adj_matrix = generate_chain_topology(n_nodes)

for i in range(1,6):
    np.savetxt("./Benchmarks/data/W_F"+str(i),adj_matrix, fmt='%.5f')
# 打印邻接矩阵
print("链式拓扑的邻接矩阵:")
print(adj_matrix)