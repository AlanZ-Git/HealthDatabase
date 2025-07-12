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

def read_version_tuple_from_txt(txt_path: str) -> tuple:
    """
    读取txt文件的第五行，将tuple数字输出
    :param txt_path: txt文件路径
    :return: tuple
    """
    with open(txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    if len(lines) < 5:
        raise ValueError("文件行数不足5行")
    line = lines[4].strip()
    # 假设格式为 filevers=(2025, 7, 12, 0),  # ...
    start = line.find('(')
    end = line.find(')', start)
    if start == -1 or end == -1:
        raise ValueError("第五行未找到tuple格式")
    tuple_str = line[start+1:end]
    # 转换为tuple
    version_tuple = tuple(int(x.strip()) for x in tuple_str.split(','))
    return version_tuple


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

        version = 'v' + '.'.join(str(x) for x in read_version_tuple_from_txt('version_info.txt'))

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