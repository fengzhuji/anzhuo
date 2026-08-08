import os
import re
import unicodedata

# 1. 动态获取 name1.py 所在的绝对目录 (/home/azazaaz121/anzhuo)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. 6 个分类文件夹名称
FOLDER_NAMES = [
    "河鲜海鲜",
    "酒水饮料",
    "冷菜",
    "热炒",
    "烧烤串串",
    "蒸菜",
]

# 3. 自动拼接生成绝对路径，彻底避免路径找不到的问题
FOLDERS = [os.path.join(BASE_DIR, name) for name in FOLDER_NAMES]

# 4. 运行模式设置：
# True  = 【仅预览模式】（只打印预览修改结果，不改变物理文件）
# False = 【真实重命名】（确认预览无误后改成 False 再次运行）
DRY_RUN = False

def sanitize_filename(filename, folder_name):
    name, ext = os.path.splitext(filename)
    if ext.lower() not in [".jpg", ".jpeg"]:
        return None  # 过滤非 JPG 文件

    # 将全角字符/数字转为半角（如 "１０" -> "10"）
    name = unicodedata.normalize("NFKC", name)

    # 提取文件名中的数字（金额）
    match = re.search(r"(\d+)", name)
    if not match:
        # 如果文件名里没有任何数字，标记为异常
        return f"[ERROR_NO_NUMBER]_{filename}"

    number = match.group(1)

    # 提取数字前面的文本作为前缀，若无前缀则默认使用文件夹名称
    prefix = name[: match.start()].strip(" _-")
    if not prefix:
        prefix = folder_name

    # 生成统一的标准文件名格式：前缀_数字元.jpg
    return f"{prefix}_{number}元{ext.lower()}"


def process_batch():
    mode_text = (
        "【仅预览模式】(不物理修改文件)" if DRY_RUN else "【真实执行重命名】"
    )
    print(f"=== 当前运行模式: {mode_text} ===\n")

    error_files = []

    for folder in FOLDERS:
        folder_basename = os.path.basename(folder)

        if not os.path.exists(folder):
            print(f"⚠️ 路径不存在，已跳过: {folder_basename} ({folder})")
            continue

        files = os.listdir(folder)
        print(f"📁 正在扫描文件夹: {folder_basename}")
        changed_count = 0

        for file in files:
            old_path = os.path.join(folder, file)
            if not os.path.isfile(old_path):
                continue

            new_file = sanitize_filename(file, folder_basename)
            if not new_file:
                continue

            # 处理未提取出数字的异常文件
            if new_file.startswith("[ERROR"):
                error_files.append((old_path, file))
                continue

            new_path = os.path.join(folder, new_file)

            if file != new_file:
                changed_count += 1
                action = "[拟修改]" if DRY_RUN else "[已修改]"
                print(f"  {action} {file}  ==>  {new_file}")
                if not DRY_RUN:
                    os.rename(old_path, new_path)

        if changed_count == 0:
            print("  （没有需要格式化的文件）")
        print("-" * 50)

    # 汇总输出没有找到数字的文件
    if error_files:
        print("\n⚠️ 以下文件未能从中提取到金额数字，请核查并手动修改：")
        for path, fname in error_files:
            print(f"  - {path}")


if __name__ == "__main__":
    process_batch()