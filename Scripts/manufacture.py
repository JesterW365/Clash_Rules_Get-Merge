import os
from tools import split_check, split_check_supply, type_conversion

def manufacture(src_dir, save_dir):
    """
    调度工具函数，从 src.md 和 supply 文件生产最终的规则组。

    Args:
        src_dir (str): 源文件目录路径（包含 src.md 和 *_supply.yaml）。
        save_dir (str): 结果规则组文件的保存目录。
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # 1. 找到 src.md 并获取基础信息
    src_md_path = os.path.join(src_dir, 'src.md')
    print(f"--- 正在解析基础规则: {src_md_path} ---")
    base_info = split_check(src_md_path) # [[group_title, group_name, r_name, r_type, r_url]]

    # 2. 获取补充记录信息
    print(f"\n--- 正在解析补充规则: {src_dir} ---")
    supply_info = split_check_supply(src_dir) # [[group_title, ruleset_name, rule_type, file_path]]

    # 3. 按 group_title 聚合所有规则
    # 格式：{title: {'name': group_name, 'rules': [[type, source], ...]}}
    groups = {}
    supply_counts = {} # 记录每个标题的补充数量

    # 处理基础规则
    for title, g_name, r_name, r_type, r_url in base_info:
        if title not in groups:
            groups[title] = {'name': g_name, 'rules': []}
        groups[title]['rules'].append([r_type, r_url])

    # 处理补充规则
    for title, r_name, r_type, r_path in supply_info:
        # 如果基础库里没有这个标题，则创建（以前12位或标题本身作为文件名）
        if title not in groups:
            groups[title] = {'name': title[:12], 'rules': []}
        groups[title]['rules'].append([r_type, r_path])
        supply_counts[title] = supply_counts.get(title, 0) + 1

    # 4. 依次调用转换和混合
    print(f"\n--- 正在生成规则组文件 ---")
    all_group_names = []
    for title, data in groups.items():
        g_name = data['name']
        all_group_names.append(g_name)
        type_conversion(g_name, save_dir, data['rules'])
    
    # 4.1 在保存目录生成 rulesets.list
    list_file_path = os.path.join(save_dir, 'rulesets.list')
    with open(list_file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_group_names) + '\n')
    print(f"已生成规则列表文件: {list_file_path}")
    
    # 5. 打印汇总信息
    print(f"\n生成了 {len(groups)} 个规则组")
    for title, count in supply_counts.items():
        group_name = groups[title]['name']
        print(f"其中 {group_name} 有 {count} 个补充")

if __name__ == "__main__":
    src_path = r"source"
    dest_path = r"Generated_rulesets"
    manufacture(src_path, dest_path)
