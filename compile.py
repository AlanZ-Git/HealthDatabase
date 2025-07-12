from operator import iconcat
import subprocess
import os
import shutil
import zipfile

def zip_folder(folder_path: str):
    """
    将指定文件夹压缩为zip文件, 保存在其父目录下。
    :param folder_path: 需要压缩的文件夹路径
    """
    folder_path = os.path.abspath(folder_path)
    parent_dir = os.path.dirname(folder_path)
    folder_name = os.path.basename(folder_path)
    zip_path = os.path.join(parent_dir, f"{folder_name}.zip")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                abs_file = os.path.join(root, file)
                rel_path = os.path.relpath(abs_file, folder_path)
                zipf.write(abs_file, arcname=os.path.join(folder_name, rel_path))
    
    return zip_path

def read_product_version_from_txt(txt_path: str) -> str:
    """
    读取txt文件第22行u'ProductVersion'的下一个字符串（即版本号字符串）
    :param txt_path: txt文件路径
    :return: 版本号字符串
    """
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    if len(lines) < 22:
        raise ValueError("文件行数不足22行")
    line = lines[21].strip()
    # 查找u'ProductVersion'后面的字符串
    import re
    match = re.search(r"u'ProductVersion'\s*,\s*u'([^']+)'", line)
    if not match:
        raise ValueError("第22行未找到ProductVersion对应的字符串")
    return match.group(1)


def compile(name: str = '就诊信息管理'):
    cmd = [
        ".venv\\Scripts\\pyinstaller.exe",
        "--name", name,
        "--windowed",
        "--onefile",
        "--version-file", "version_info.txt",
        "main.py"
    ]
    try:
        subprocess.run(cmd, check=True)
        print("封装完成")

        compile_exe = f'dist/{name}.exe'
        default_ini = 'settings.ini'
        icon = 'icon.png'

        version = 'v' + read_product_version_from_txt('version_info.txt')

        dir_path = f'dist/{name}'
        os.makedirs(dir_path, exist_ok=True)

        shutil.copy2(compile_exe, dir_path)
        os.remove(compile_exe)

        shutil.copy2(default_ini, dir_path)
        shutil.copy2(icon, dir_path)

        zip_path = zip_folder(dir_path)
        new_zip_path = f'dist/{name}_{version}.zip'
        os.rename(zip_path, new_zip_path)
        shutil.rmtree(dir_path)

        print(f'打包完成')

    except subprocess.CalledProcessError as e:
        print("打包过程中发生错误：", e)

if __name__ == "__main__":
    compile()