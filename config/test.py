import json


def parse_json_from_file(file_path):
    # 打开文件并读取数据
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # 遍历每个物种
    for model in data['curated_models']:
        specie = model['specie']
        print(f"物种: {specie}")

        # 遍历每个物种中的种群
        for population in model['populations']:
            pop = population['population']
            phe = population['phe']
            geno = population['geno']
            print(f"  种群: {pop}, 表型: {phe}, 基因型: {geno}")


# 文件路径，确保这个路径指向你的JSON文件
file_path = 'curated_models.json'

# 调用函数
parse_json_from_file(file_path)
