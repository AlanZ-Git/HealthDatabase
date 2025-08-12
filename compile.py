# -*- coding: utf-8 -*-
"""
本脚本用于将主程序(main.py)打包为可执行文件，并自动处理版本号、资源文件的拷贝和最终压缩归档。
"""

from operator import iconcat
import subprocess
import os
import shutil
import zipfile

def zip_folder(folder_path: str):
    """
    将指定文件夹压缩为zip文件, 保存在其父目录下。
    :param folder_path: 需要压缩的文件夹路径
    :return: 压缩后的zip文件路径
    """
    folder_path = os.path.abspath(folder_path)
    parent_dir = os.path.dirname(folder_path)
    folder_name = os.path.basename(folder_path)
    zip_path = os.path.join(parent_dir, f"{folder_name}.zip")

    # 创建zip文件并写入文件夹内容
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                abs_file = os.path.join(root, file)
                rel_path = os.path.relpath(abs_file, folder_path)
                # 保持文件夹结构
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
    line = lines[21].strip()  # 第22行（下标21）
    # 查找u'ProductVersion'后面的字符串
    import re
    match = re.search(r"u'ProductVersion'\s*,\s*u'([^']+)'", line)
    if not match:
        raise ValueError("第22行未找到ProductVersion对应的字符串")
    return match.group(1)


def compile(name: str = '就诊信息管理'):
    """
    使用PyInstaller将主程序(main.py)打包为单文件可执行程序，并自动处理资源文件和版本号。
    :param name: 生成的可执行文件名称
    """
    # 构建PyInstaller命令
    cmd = [
        ".venv\\Scripts\\pyinstaller.exe",  # 虚拟环境下的pyinstaller路径
        "--name", name,                      # 指定生成的exe名称
        "--windowed",                        # 无控制台窗口
        "--onefile",                         # 单文件打包
        "--version-file", "version_info.txt",# 指定版本信息文件
        "main.py"                            # 主程序入口
    ]
    try:
        # 执行打包命令
        subprocess.run(cmd, check=True)
        print("封装完成")

        compile_exe = f'dist/{name}.exe'      # 打包生成的exe路径
        default_ini = 'settings.ini'          # 配置文件
        icon = 'icon.png'                     # 程序图标

        # 读取版本号，前缀加v
        version = 'v' + read_product_version_from_txt('version_info.txt')

        dir_path = f'dist/{name}'             # 临时目录用于归档
        os.makedirs(dir_path, exist_ok=True)

        # 拷贝exe到临时目录，并删除原始exe
        shutil.copy2(compile_exe, dir_path)
        os.remove(compile_exe)

        # 拷贝配置文件和图标到临时目录
        shutil.copy2(default_ini, dir_path)
        shutil.copy2(icon, dir_path)

        # 压缩临时目录为zip包
        zip_path = zip_folder(dir_path)
        new_zip_path = f'dist/{name}_{version}.zip'  # 带版本号的zip包
        os.rename(zip_path, new_zip_path)
        shutil.rmtree(dir_path)  # 删除临时目录

        print(f'打包完成')

    except subprocess.CalledProcessError as e:
        print("打包过程中发生错误：", e)


if __name__ == "__main__":
    compile()