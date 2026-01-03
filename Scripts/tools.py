import re
import requests
import os

def split_check(file_path):
    """
    分割并检查 md 文件中的规则信息。

    Args:
        file_path (str): src.md 文件的绝对路径。

    Returns:
        list: 返回复合列表 [[group_title, group_name, r_name, r_type, r_url], ...]
    """
    if not os.path.exists(file_path):
        print(f"错误: 文件 {file_path} 不存在。")
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    # 补全末尾的 --- 以便正则表达式匹配最后一个块
    if not content.endswith('---'):
        content += '\n---'

    pattern = re.compile(r'(###.*?---)', re.DOTALL)
    parts = pattern.findall(content)

    if not parts:
        print("提示：文件内容有误，无法按照 '### {规则组标题}... ---' 形式分割，无法split。")
        return []

    total_rules_count = 0
    passed_rules_count = 0
    results = []

    for part in parts:
        # 提取标题
        title_match = re.search(r'###\s*(.*?)(\n|$)', part)
        if not title_match:
             continue
        
        group_title = title_match.group(1).strip()
        if not group_title:
            # 规则组标题为空
            print("规则组标题为空，已跳过该部分")
            continue

        # 提取 name 参数
        name_search = re.search(r'name\s*:\s*(.*?)(\n|$)', part)
        group_name = ""
        if name_search:
            group_name = name_search.group(1).strip()
        
        # 如果 name 参数为空或空格，按无参数处理
        if not group_name:
            group_name = group_title[:12]

        # 提取内部规则
        rule_pattern = re.compile(r'(?:(?:\d+\.\s*)?([^\n\r-]+))[\s\n\r]*- type\s*:\s*(.*?)[\s\n\r]*- url\s*:\s*(.*?)(?:\n|$|---)', re.DOTALL)
        rules_found = rule_pattern.findall(part)

        if not rules_found:
            # 不满足规则格式
            print(f"{group_title} 内部不满足规则格式，已跳过")
            continue

        for r_name, r_type, r_url in rules_found:
            total_rules_count += 1
            r_name = r_name.strip()
            r_type = r_type.strip()
            r_url = r_url.strip().strip("'")

            # 检查规则名是否为空
            if not r_name:
                print(f"{group_title} 的某些规则名为空，已跳过")
                continue

            # 检查规则类型
            valid_types = ['classical', 'domain', 'ipcidr']
            if r_type not in valid_types:
                print(f"{group_title}-{group_name}-{r_name} 的规则类型 {r_type} 非法，已跳过")
                continue

            # 仅检查连通性 (不需要检查是否为空，因为正则匹配到的 url 如果为空也会进入报错逻辑，或者直接导致正则不匹配)
            # 用户要求：仅检查是否可以连通即可
            try:
                # 连通性测试
                resp = requests.get(r_url, timeout=5, stream=True)
                if resp.status_code >= 400:
                    raise Exception(f"HTTP {resp.status_code}")
            except Exception:
                # 组合形式：规则组标题, 规则组名, 其内规则名, 规则类型, 规则链接
                print(f"{group_title}-{group_name}-{r_type}-{r_url} 无法连通")
                continue

            passed_rules_count += 1
            results.append([group_title, group_name, r_name, r_type, r_url])

    print(f"检查完毕，通过: {passed_rules_count}/{total_rules_count}")
    return results

def split_check_supply(directory):
    """
    检查目标路径里的所有 {*_supply.yaml} 文件的内容和格式。

    Args:
        directory (str): 包含 supply yaml 文件的目录路径。

    Returns:
        list: 返回复合列表 [[group_title, r_name, r_type, r_path], ...]
    """
    if not os.path.exists(directory):
        print(f"错误: 目录 {directory} 不存在。")
        return []

    files = [f for f in os.listdir(directory) if f.endswith('_supply.yaml')]
    total_files = len(files)
    passed_files = 0
    results = []

    for filename in files:
        file_path = os.path.join(directory, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取元数据
        # 使用 MULTILINE 模式和锚点 ^ $ 来确保严格按行匹配，避免匹配到下一行的内容
        # 增加对 \r 的显式排除或确保 $ 能正确处理不同平台的换行
        group_title_match = re.findall(r'^###\s*(.*?)\r?$', content, re.MULTILINE)
        ruleset_match = re.findall(r'^# ruleset\s*:\s*(.*?)\r?$', content, re.MULTILINE)
        type_match = re.findall(r'^# type\s*:\s*(.*?)\r?$', content, re.MULTILINE)

        if len(group_title_match) != 1 or len(ruleset_match) != 1 or len(type_match) != 1:
            print(f"{filename} 跳过原因：元数据格式错误或不唯一")
            continue

        group_title = group_title_match[0].strip()
        ruleset_name = ruleset_match[0].strip()
        rule_type = type_match[0].strip()

        # 如果任一为空，则跳过
        if not group_title or not ruleset_name or not rule_type:
            print(f"{filename} 跳过原因：元数据字段 (标题/名称/类型) 不能为空")
            continue

        # 检查规则类型是否合法
        valid_types = ['classical', 'domain', 'ipcidr']
        if rule_type not in valid_types:
            print(f"{group_title}-{ruleset_name}-{rule_type}-{filename} 的类型非法，已跳过")
            continue

        # 检查信息内容（元数据之后的部分）
        # 移除元数据行来检查剩余内容
        clean_content = re.sub(r'###.*?\n|# ruleset.*?\n|# type.*?\n', '', content).strip()
        
        if not clean_content:
            print(f"{group_title}-{ruleset_name}-{rule_type}-{filename} 规则内容为空，已跳过")
            continue

        # 检查通过
        passed_files += 1
        results.append([group_title, ruleset_name, rule_type, file_path])

    print(f"检查完毕，通过: {passed_files}/{total_files}")
    return results

def type_conversion(group_name, save_dir, rule_list):
    """
    将 domain 和 ipcidr 类型的规则转换为 classical 形式并合并去重。

    Args:
        group_name (str): 生成的规则组文件名（不含扩展名）。
        save_dir (str): 生成文件的保存目录路径。
        rule_list (list): 复合列表 [[类型, url或文件路径], ...]，列表不能为空。

    Returns:
        None: 函数直接在指定位置生成 YAML 文件并打印统计信息。
    """
    import datetime
    
    if not group_name or not save_dir or not rule_list:
        print("错误: 缺少必要参数或 rule_list 为空。")
        return

    valid_types = ['classical', 'domain', 'ipcidr']
    final_rules_set = set()
    all_converted_rules = [] # 存储所有转换成功的条目，用于计算重复
    
    total_sources = len(rule_list)
    success_sources = 0
    actual_all_lines_count = 0 # 不包括空行和注释行的总条数

    for r_type, r_source in rule_list:
        if r_type not in valid_types:
            print(f"提示: 类型 {r_type} 不在处理范围内，已跳过。")
            continue

        try:
            # 读取内容
            if r_source.startswith(('http://', 'https://')):
                content = requests.get(r_source, timeout=10).text
            else:
                with open(r_source, 'r', encoding='utf-8') as f:
                    content = f.read()
        except Exception:
            print(f"无法读取规则源: {r_source}")
            continue

        success_sources += 1
        lines = content.splitlines()
        
        for line in lines:
            line = line.strip()
            
            # 1. 移除注释和空行
            if not line or line.startswith('#'):
                continue
            
            # 此时属于“实际所有的规则条数”
            actual_all_lines_count += 1
            
            # 2. 忽略 payload:
            if line.startswith('payload:'):
                actual_all_lines_count -= 1 # payload 行不计入有效规则条数
                continue

            # 3. 处理 YAML 数组格式的短横线
            if line.startswith('-'):
                line = line[1:].strip()
            
            # 4. 移除可能的单/双引号
            line = line.strip("'\"")

            converted_line = None
            
            if r_type == 'classical':
                converted_line = line
            elif r_type == 'domain':
                if line.startswith('+.'):
                    converted_line = f"DOMAIN-SUFFIX,{line[2:]}"
                elif line.startswith('.'):
                    converted_line = f"DOMAIN-SUFFIX,{line[1:]}"
                elif '*' in line:
                    # 将包含 * 的规则处理为 DOMAIN-SUFFIX 形式
                    # 移除开头的 * 和 . 字符，取其后缀
                    # 例如 *.*.microsoft.com -> microsoft.com
                    domain_part = line.lstrip('*.')
                    if domain_part:
                        converted_line = f"DOMAIN-SUFFIX,{domain_part}"
                else:
                    converted_line = f"DOMAIN,{line}"
            elif r_type == 'ipcidr':
                converted_line = f"IP-CIDR,{line}"

            if converted_line:
                all_converted_rules.append(converted_line)
                final_rules_set.add(converted_line)

    # 统计
    success_converted_count = len(all_converted_rules) # 成功合并规则的条数
    final_unique_count = len(final_rules_set)
    duplicate_count = success_converted_count - final_unique_count

    # 生成结果
    save_file = os.path.join(save_dir, f"{group_name}.yaml")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(save_file, 'w', encoding='utf-8') as f:
        f.write(f"# Generated on: {now}\n")
        f.write("payload:\n")
        for rule in sorted(list(final_rules_set)):
            f.write(f"  - {rule}\n")

    print(f"合并了 {success_sources} / {total_sources} 个规则，包含了 {success_converted_count} / {actual_all_lines_count} 条规则，去除了 {duplicate_count} 条重复规则")
